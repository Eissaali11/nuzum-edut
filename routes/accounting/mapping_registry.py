"""Central mapping registry for accounting legacy endpoints.

Phase-0 source of truth for compatibility aliases.
"""

from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class EndpointMapping:
    legacy_endpoint: str
    canonical_endpoint: str
    legacy_rule: str
    methods: Sequence[str] = ("GET",)
    critical: bool = False


# Team reference table (legacy -> canonical)
LEGACY_ENDPOINT_MAPPINGS: List[EndpointMapping] = [
    EndpointMapping("salaries.index", "payroll.process", "/salaries/", ("GET",), True),
    EndpointMapping("salaries.report", "reports.salaries_report", "/salaries/report", ("GET",), True),
    EndpointMapping("salaries.create", "payroll.process", "/salaries/create", ("GET", "POST"), True),
    EndpointMapping("salaries.import_excel", "payroll.process", "/salaries/import", ("GET", "POST"), True),
    EndpointMapping("salaries.export_excel", "reports.salaries_excel", "/salaries/export", ("GET",), True),
    EndpointMapping("salaries.report_pdf", "reports.salaries_report_pdf", "/salaries/report/pdf", ("GET",), True),
    EndpointMapping("salaries.batch_salary_notifications", "payroll.process", "/salaries/notifications/batch", ("GET", "POST"), True),
    EndpointMapping("salaries.batch_deduction_notifications", "payroll.process", "/salaries/notifications/deduction/batch", ("GET", "POST"), True),
    EndpointMapping("salaries.edit", "payroll.process", "/salaries/<int:id>/edit", ("GET", "POST"), True),
    EndpointMapping("salaries.salary_notification_pdf", "reports.salaries_pdf", "/salaries/notification/<int:id>/pdf", ("GET",), True),

    EndpointMapping("accounting.accounts", "accounting_accounts.accounts", "/accounting/accounts", ("GET",), True),
    EndpointMapping("accounting.create_account", "accounting_accounts.create_account", "/accounting/accounts/create", ("GET", "POST"), True),
    EndpointMapping("accounting.edit_account", "accounting_accounts.edit_account", "/accounting/accounts/<int:account_id>/edit", ("GET", "POST"), True),
    EndpointMapping("accounting.confirm_delete_account", "accounting_accounts.confirm_delete_account", "/accounting/accounts/<int:account_id>/confirm-delete", ("GET", "POST"), True),

    EndpointMapping("accounting.chart_of_accounts", "accounting_charts.chart_of_accounts", "/accounting/chart-of-accounts", ("GET",), True),
    EndpointMapping("accounting.create_default_accounts", "accounting_charts.create_default_accounts", "/accounting/create-default-accounts", ("POST",), True),
    EndpointMapping("accounting.account_balance_page", "accounting_charts.account_balance_page", "/accounting/account/<int:account_id>/balance-page", ("GET",), True),
    EndpointMapping("accounting.delete_account", "accounting_charts.delete_account", "/accounting/account/<int:account_id>/delete", ("POST",), True),

    EndpointMapping("accounting.transactions", "accounting_transactions.transactions", "/accounting/transactions", ("GET",), True),
    EndpointMapping("accounting.add_transaction", "accounting_transactions.add_transaction", "/accounting/transactions/new", ("GET", "POST"), True),
    EndpointMapping("accounting.create_journal_entry", "accounting_transactions.add_transaction", "/accounting/journal-entries/new", ("GET", "POST"), True),
    EndpointMapping("accounting.view_transaction", "accounting_transactions.view_transaction", "/accounting/transaction/<int:transaction_id>", ("GET",), True),

    EndpointMapping("accounting.cost_centers", "accounting_costcenters.cost_centers", "/accounting/cost-centers", ("GET",), True),
    EndpointMapping("accounting.create_cost_center", "accounting_costcenters.create_cost_center", "/accounting/cost-centers/create", ("GET", "POST"), True),
    EndpointMapping("accounting.view_cost_center", "accounting_costcenters.view_cost_center", "/accounting/cost-centers/<int:center_id>", ("GET",), True),
    EndpointMapping("accounting.edit_cost_center", "accounting_costcenters.edit_cost_center", "/accounting/cost-centers/<int:center_id>/edit", ("GET", "POST"), True),

    EndpointMapping("accounting.analytics", "analytics_simple.dashboard", "/accounting/analytics", ("GET",), True),
    EndpointMapping("accounting.trial_balance", "accounting_ext.trial_balance", "/accounting/trial-balance", ("GET",), True),
    EndpointMapping("accounting.balance_sheet", "accounting_ext.balance_sheet", "/accounting/balance-sheet", ("GET",), True),

    EndpointMapping("accounting.journal_entries", "accounting_transactions.transactions", "/accounting/journal-entries", ("GET",), True),
    EndpointMapping("accounting.pending_transactions", "accounting_transactions.transactions", "/accounting/pending-transactions", ("GET",), True),
    EndpointMapping("accounting.settings", "accounting.dashboard", "/accounting/settings", ("GET",), True),
    EndpointMapping("accounting.fiscal_years", "accounting.dashboard", "/accounting/fiscal-years", ("GET",), True),
    EndpointMapping("accounting.income_statement", "accounting.dashboard", "/accounting/income-statement", ("GET",), True),
    EndpointMapping("accounting.customers", "accounting.dashboard", "/accounting/customers", ("GET",), True),
    EndpointMapping("accounting.vendors", "accounting.dashboard", "/accounting/vendors", ("GET",), True),
    EndpointMapping("accounting.edit_transaction", "accounting_transactions.transactions", "/accounting/transactions/<int:transaction_id>/edit", ("GET", "POST"), True),
]


def get_critical_mappings() -> List[EndpointMapping]:
    return [m for m in LEGACY_ENDPOINT_MAPPINGS if m.critical]
