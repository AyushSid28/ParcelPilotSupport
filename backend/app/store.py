from __future__ import annotations

from dataclasses import dataclass

from app.auth import NotFound, visible_account
from app.mapping import account_from_row, order_from_row, ticket_from_row
from app.models import Account, Actor, Order, Ticket


@dataclass
class Store:
    conn: object

    def account(self, actor: Actor, account_id: str) -> Account:
        if not visible_account(actor, account_id):
            raise NotFound()
        row = self.conn.execute("SELECT * FROM accounts WHERE account_id=?", (account_id,)).fetchone()
        if not row:
            raise NotFound()
        return account_from_row(row)

    def order(self, actor: Actor, order_id: str) -> Order:
        row = self.conn.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
        if not row or not visible_account(actor, row["account_id"]):
            raise NotFound()
        return order_from_row(row)

    def ticket(self, actor: Actor, ticket_id: str) -> Ticket:
        row = self.conn.execute("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
        if not row or not visible_account(actor, row["account_id"]):
            raise NotFound()
        return ticket_from_row(row)

    def orders(self, actor: Actor, account_id: str | None = None) -> list[Order]:
        sql = "SELECT * FROM orders"
        params: list = []
        if actor.kind == "customer":
            sql += " WHERE account_id=?"
            params.append(actor.account_id)
        elif account_id:
            sql += " WHERE account_id=?"
            params.append(account_id)
        sql += " ORDER BY order_id"
        return [order_from_row(r) for r in self.conn.execute(sql, params)]

    def tickets(self, actor: Actor, account_id: str | None = None, status: str | None = None) -> list[Ticket]:
        clauses = []
        params: list = []
        if actor.kind == "customer":
            clauses.append("account_id=?")
            params.append(actor.account_id)
        elif account_id:
            clauses.append("account_id=?")
            params.append(account_id)
        if status:
            clauses.append("status=?")
            params.append(status)
        sql = "SELECT * FROM tickets"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at"
        return [ticket_from_row(r) for r in self.conn.execute(sql, params)]

    def accounts(self, actor: Actor) -> list[Account]:
        if actor.kind == "customer":
            return [self.account(actor, actor.account_id)]
        rows = self.conn.execute("SELECT * FROM accounts ORDER BY account_id")
        return [account_from_row(r) for r in rows]
