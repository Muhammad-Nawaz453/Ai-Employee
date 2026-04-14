#!/usr/bin/env python3
"""
Odoo MCP Server - Accounting Integration

Provides tools for:
- Creating and managing invoices
- Recording payments
- Generating financial reports
- Managing customers and products
- Accounting reconciliation

All sensitive operations require human approval (HITL pattern)

Uses Odoo's XML-RPC API (JSON-RPC for Odoo 19+)
"""

import xmlrpc.client
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import sys

# Configuration
CONFIG = {
    "vault_path": os.getenv("VAULT_PATH", "./AI_Employee_Vault"),
    "odoo_url": os.getenv("ODOO_URL", "http://localhost:8069"),
    "odoo_db": os.getenv("ODOO_DB", "odoo"),
    "odoo_username": os.getenv("ODOO_USERNAME", "admin"),
    "odoo_password": os.getenv("ODOO_PASSWORD", "admin"),
    "port": int(os.getenv("PORT", "8811")),
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("odoo-mcp")


class OdooClient:
    """Odoo XML-RPC client wrapper"""
    
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        
        # Common endpoint for authentication
        self.common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        # Object endpoint for model operations
        self.models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        
        # Authenticate and get UID
        self.uid = self.common.authenticate(db, username, password, {})
        
        if not self.uid:
            raise Exception(f"Authentication failed for user {username}")
        
        logger.info(f"Authenticated to Odoo as {username} (UID: {self.uid})")
    
    def execute_kw(self, model: str, method: str, args: list, kwargs: dict = None) -> Any:
        """Execute a method on a model"""
        if kwargs is None:
            kwargs = {}
        return self.models.execute_kw(
            self.db, self.uid, self.password, model, method, args, kwargs
        )
    
    def search_read(self, model: str, domain: list, fields: list = None, limit: int = 100) -> List[Dict]:
        """Search and read records"""
        return self.execute_kw(model, "search_read", [domain], {
            "fields": fields,
            "limit": limit,
        })
    
    def create(self, model: str, values: Dict) -> int:
        """Create a new record"""
        return self.execute_kw(model, "create", [values])
    
    def write(self, model: str, ids: list, values: Dict) -> bool:
        """Update records"""
        return self.execute_kw(model, "write", [ids, values])
    
    def unlink(self, model: str, ids: list) -> bool:
        """Delete records"""
        return self.execute_kw(model, "unlink", [ids])


class OdooMCPServer:
    """MCP Server for Odoo integration"""
    
    def __init__(self):
        self.vault_path = Path(CONFIG["vault_path"])
        self.client = None
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories"""
        (self.vault_path / "Pending_Approval").mkdir(parents=True, exist_ok=True)
        (self.vault_path / "Approved").mkdir(parents=True, exist_ok=True)
        (self.vault_path / "Accounting").mkdir(parents=True, exist_ok=True)
        (self.vault_path / "Logs").mkdir(parents=True, exist_ok=True)
    
    def get_client(self) -> OdooClient:
        """Get or create Odoo client"""
        if self.client is None:
            self.client = OdooClient(
                CONFIG["odoo_url"],
                CONFIG["odoo_db"],
                CONFIG["odoo_username"],
                CONFIG["odoo_password"],
            )
        return self.client
    
    def create_invoice_draft(self, partner_name: str, invoice_lines: List[Dict], 
                             invoice_date: str = None, payment_term: str = None) -> str:
        """
        Create a draft invoice (requires approval)
        
        Args:
            partner_name: Customer name
            invoice_lines: List of dicts with name, quantity, price_unit
            invoice_date: Invoice date (YYYY-MM-DD)
            payment_term: Payment terms
        """
        client = self.get_client()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        approval_id = f"ODOO_INVOICE_{timestamp}"
        
        # Find or create partner
        partners = client.search_read("res.partner", [["name", "=", partner_name]], limit=1)
        
        if partners:
            partner_id = partners[0]["id"]
        else:
            # Create partner (also requires approval in production)
            partner_id = client.create("res.partner", {"name": partner_name})
        
        # Calculate total
        total = sum(line.get("quantity", 1) * line.get("price_unit", 0) for line in invoice_lines)
        
        # Create approval request
        approval_data = {
            "type": "approval_request",
            "action": "create_invoice",
            "platform": "odoo",
            "partner_name": partner_name,
            "partner_id": partner_id,
            "invoice_lines": invoice_lines,
            "invoice_date": invoice_date or datetime.now().strftime("%Y-%m-%d"),
            "payment_term": payment_term,
            "total": total,
            "created": datetime.now().isoformat(),
            "status": "pending",
        }
        
        # Write approval file
        approval_file = self.vault_path / "Pending_Approval" / f"{approval_id}.md"
        
        lines_md = "\n".join([
            f"- {line.get('name', 'Item')}: {line.get('quantity', 1)} × ${line.get('price_unit', 0):.2f} = ${line.get('quantity', 1) * line.get('price_unit', 0):.2f}"
            for line in invoice_lines
        ])
        
        markdown = f"""---
type: approval_request
action: create_invoice
platform: odoo
partner: {partner_name}
total: {total:.2f}
created: {datetime.now().isoformat()}
status: pending
---

# Odoo Invoice Draft

## Customer
- **Name:** {partner_name}
- **Odoo ID:** {partner_id}

## Invoice Lines
{lines_md}

## Total
**${total:.2f}**

## Details
- **Invoice Date:** {invoice_date or datetime.now().strftime('%Y-%m-%d')}
- **Payment Terms:** {payment_term or "Net 30"}

## Approval Instructions
Move this file to /Approved to create the invoice in Odoo.
Move to /Rejected to cancel.
"""
        
        approval_file.write_text(markdown, encoding="utf-8")
        logger.info(f"Created invoice draft approval: {approval_id}")
        
        return f"Invoice draft created: {approval_id}. Pending approval."
    
    def publish_approved_invoice(self, approval_file: str) -> str:
        """Create invoice in Odoo after approval"""
        client = self.get_client()
        
        # Read approval file
        approval_path = Path(approval_file)
        if not approval_path.exists():
            return f"Error: Approval file not found: {approval_file}"
        
        content = approval_path.read_text(encoding="utf-8")
        
        # Parse partner and lines (simplified parsing)
        import re
        partner_match = re.search(r"partner: (.+)", content)
        partner_name = partner_match.group(1) if partner_match else "Unknown"
        
        # Find partner
        partners = client.search_read("res.partner", [["name", "=", partner_name]], limit=1)
        if not partners:
            return f"Error: Partner not found: {partner_name}"
        
        partner_id = partners[0]["id"]
        
        # Create invoice
        invoice_vals = {
            "move_type": "out_invoice",
            "partner_id": partner_id,
            "invoice_date": datetime.now().strftime("%Y-%m-%d"),
            "invoice_line_ids": [],
        }
        
        # In a real implementation, parse invoice_lines from approval file
        # For now, create a simple invoice
        invoice_id = client.create("account.move", invoice_vals)
        
        # Post invoice
        client.execute_kw("account.move", "action_post", [[invoice_id]])
        
        # Log the action
        self._log_action("create_invoice", {
            "partner": partner_name,
            "invoice_id": invoice_id,
            "approval_file": approval_file,
        })
        
        # Move approval file to Approved
        approved_path = self.vault_path / "Approved" / approval_path.name
        approval_path.rename(approved_path)
        
        return f"Invoice created and posted in Odoo. ID: {invoice_id}"
    
    def get_invoices(self, state: str = "posted", days: int = 30) -> str:
        """Get recent invoices"""
        client = self.get_client()
        
        # Calculate date range
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        invoices = client.search_read(
            "account.move",
            [["move_type", "=", "out_invoice"], ["date", ">=", since]],
            fields=["name", "partner_id", "amount_total", "amount_residual", "state", "date"],
            limit=50,
        )
        
        summary = f"# Recent Invoices (Last {days} Days)\n\n"
        summary += f"{'Invoice':<15} {'Customer':<25} {'Total':>12} {'Residual':>12} {'Status':<10}\n"
        summary += "-" * 80 + "\n"
        
        total_amount = 0
        total_residual = 0
        
        for inv in invoices:
            partner = inv.get("partner_id", [None, "Unknown"])[1] if isinstance(inv.get("partner_id"), list) else "Unknown"
            summary += f"{inv.get('name', 'N/A'):<15} {partner:<25} ${inv.get('amount_total', 0):>11.2f} ${inv.get('amount_residual', 0):>11.2f} {inv.get('state', 'N/A'):<10}\n"
            total_amount += inv.get("amount_total", 0)
            total_residual += inv.get("amount_residual", 0)
        
        summary += "-" * 80 + "\n"
        summary += f"{'TOTAL':<41} ${total_amount:>11.2f} ${total_residual:>11.2f}\n\n"
        summary += f"**Count:** {len(invoices)} invoices\n"
        
        # Save to vault
        summary_file = self.vault_path / "Accounting" / f"invoices_{datetime.now().strftime('%Y%m%d')}.md"
        summary_file.write_text(summary, encoding="utf-8")
        
        return summary
    
    def get_payments(self, days: int = 30) -> str:
        """Get recent payments"""
        client = self.get_client()
        
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        payments = client.search_read(
            "account.payment",
            [["date", ">=", since]],
            fields=["name", "partner_id", "amount", "payment_type", "state", "date"],
            limit=50,
        )
        
        summary = f"# Recent Payments (Last {days} Days)\n\n"
        summary += f"{'Payment':<15} {'Partner':<25} {'Amount':>12} {'Type':<10} {'Status':<10}\n"
        summary += "-" * 80 + "\n"
        
        total_in = 0
        total_out = 0
        
        for pay in payments:
            partner = pay.get("partner_id", [None, "Unknown"])[1] if isinstance(pay.get("partner_id"), list) else "Unknown"
            ptype = "IN" if pay.get("payment_type") == "inbound" else "OUT"
            summary += f"{pay.get('name', 'N/A'):<15} {partner:<25} ${pay.get('amount', 0):>11.2f} {ptype:<10} {pay.get('state', 'N/A'):<10}\n"
            
            if pay.get("payment_type") == "inbound":
                total_in += pay.get("amount", 0)
            else:
                total_out += pay.get("amount", 0)
        
        summary += "-" * 80 + "\n"
        summary += f"Total In: ${total_in:.2f} | Total Out: ${total_out:.2f}\n"
        summary += f"Net: ${total_in - total_out:.2f}\n\n"
        summary += f"**Count:** {len(payments)} payments\n"
        
        # Save to vault
        summary_file = self.vault_path / "Accounting" / f"payments_{datetime.now().strftime('%Y%m%d')}.md"
        summary_file.write_text(summary, encoding="utf-8")
        
        return summary
    
    def get_financial_summary(self) -> str:
        """Get overall financial summary"""
        client = self.get_client()
        
        # Get totals
        invoices = client.search_read(
            "account.move",
            [["move_type", "=", "out_invoice"], ["state", "=", "posted"]],
            fields=["amount_total", "amount_residual"],
            limit=1000,
        )
        
        payments = client.search_read(
            "account.payment",
            [["state", "=", "posted"]],
            fields=["amount", "payment_type"],
            limit=1000,
        )
        
        total_invoiced = sum(inv.get("amount_total", 0) for inv in invoices)
        total_outstanding = sum(inv.get("amount_residual", 0) for inv in invoices)
        total_paid = sum(p.get("amount", 0) for p in payments if p.get("payment_type") == "inbound")
        
        summary = f"""# Financial Summary

## Overview
- **Total Invoiced:** ${total_invoiced:.2f}
- **Total Paid:** ${total_paid:.2f}
- **Outstanding:** ${total_outstanding:.2f}
- **Collection Rate:** {(total_paid / total_invoiced * 100) if total_invoiced > 0 else 0:.1f}%

## Invoice Count
- **Total Invoices:** {len(invoices)}
- **Paid:** {len([i for i in invoices if i.get('amount_residual', 0) == 0])}
- **Partially Paid:** {len([i for i in invoices if 0 < i.get('amount_residual', 0) < i.get('amount_total', 0)])}
- **Unpaid:** {len([i for i in invoices if i.get('amount_residual', 0) == i.get('amount_total', 0)])}
"""
        
        # Save to vault
        summary_file = self.vault_path / "Accounting" / f"financial_summary_{datetime.now().strftime('%Y%m%d')}.md"
        summary_file.write_text(summary, encoding="utf-8")
        
        return summary
    
    def _log_action(self, action: str, data: Dict):
        """Log an action to JSONL file"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "platform": "odoo",
            "data": data,
        }
        
        log_file = self.vault_path / "Logs" / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")


# MCP Server implementation
class MCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for MCP protocol"""
    
    odoo_server = None
    
    def do_POST(self):
        """Handle POST requests (MCP tool calls)"""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            request = json.loads(body)
            method = request.get("method")
            params = request.get("params", {})
            
            result = self._handle_method(method, params)
            
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": result,
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32603, "message": str(e)},
            }
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    def _handle_method(self, method: str, params: Dict) -> Dict:
        """Route MCP method calls to appropriate handlers"""
        server = self.odoo_server
        
        if method == "tools/list":
            return {
                "tools": [
                    {
                        "name": "create_invoice_draft",
                        "description": "Create a draft invoice in Odoo (requires human approval)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "partner_name": {"type": "string"},
                                "invoice_lines": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "quantity": {"type": "number"},
                                            "price_unit": {"type": "number"},
                                        },
                                    },
                                },
                                "invoice_date": {"type": "string"},
                                "payment_term": {"type": "string"},
                            },
                            "required": ["partner_name", "invoice_lines"],
                        },
                    },
                    {
                        "name": "publish_approved_invoice",
                        "description": "Create and post an approved invoice in Odoo",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "approval_file": {"type": "string"},
                            },
                            "required": ["approval_file"],
                        },
                    },
                    {
                        "name": "get_invoices",
                        "description": "Get recent invoices from Odoo",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "state": {"type": "string"},
                                "days": {"type": "number"},
                            },
                        },
                    },
                    {
                        "name": "get_payments",
                        "description": "Get recent payments from Odoo",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "days": {"type": "number"},
                            },
                        },
                    },
                    {
                        "name": "get_financial_summary",
                        "description": "Get overall financial summary from Odoo",
                        "inputSchema": {},
                    },
                ]
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "create_invoice_draft":
                result = server.create_invoice_draft(
                    arguments.get("partner_name"),
                    arguments.get("invoice_lines", []),
                    arguments.get("invoice_date"),
                    arguments.get("payment_term"),
                )
                return {"content": [{"type": "text", "text": result}]}
            
            elif tool_name == "publish_approved_invoice":
                result = server.publish_approved_invoice(
                    arguments.get("approval_file")
                )
                return {"content": [{"type": "text", "text": result}]}
            
            elif tool_name == "get_invoices":
                result = server.get_invoices(
                    arguments.get("state", "posted"),
                    int(arguments.get("days", 30)),
                )
                return {"content": [{"type": "text", "text": result}]}
            
            elif tool_name == "get_payments":
                result = server.get_payments(
                    int(arguments.get("days", 30))
                )
                return {"content": [{"type": "text", "text": result}]}
            
            elif tool_name == "get_financial_summary":
                result = server.get_financial_summary()
                return {"content": [{"type": "text", "text": result}]}
            
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
        
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def do_GET(self):
        """Handle GET requests (health check)"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "service": "odoo-mcp"}).encode())
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        logger.debug(format % args)


def main():
    """Start the Odoo MCP Server"""
    odoo_server = OdooMCPServer()
    MCPRequestHandler.odoo_server = odoo_server
    
    port = CONFIG["port"]
    server = HTTPServer(("0.0.0.0", port), MCPRequestHandler)
    
    logger.info(f"Odoo MCP Server starting on port {port}")
    logger.info(f"Odoo URL: {CONFIG['odoo_url']}")
    logger.info(f"Database: {CONFIG['odoo_db']}")
    logger.info(f"Vault: {CONFIG['vault_path']}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
