import os

def includeme(config):
    # organisation
    config.add_route("organisation", "/organisation")
    config.add_route("organisation_gstin", "/organisation/gstin")
    config.add_route("organisation_attachment", "/organisation/attachment")
    config.add_route("organisation_gst_accounts", "/organisation/gst_accounts")
    config.add_route(
        "organisation_gst_accounts_codes", "/organisation/gst_accounts/codes"
    )
    config.add_route("organisation_registration", "/organisation/check_registration")
    config.add_route("organisation_orgname", "/organisation/check/{orgname}")
    config.add_route("organisation_rm_user", "/organisation/remove-user")

    # gkuser
    config.add_route("gkuser", "/gkuser")
    config.add_route("organisation_gkusers", "/organisation/gkusers")
    config.add_route("gkuser_orgs", "/gkuser/orgs")
    config.add_route("gkuser_role", "/gkuser/role")
    config.add_route("gkuser_pwd_question", "/gkuser/pwd/question")
    config.add_route("gkuser_pwd_answer", "/gkuser/pwd/answer")
    config.add_route("gkuser_pwd_reset", "/gkuser/pwd/reset")
    config.add_route("gkuser_change_pwd", "/gkuser/pwd/change")
    config.add_route("gkuser_pwd_validate", "/gkuser/pwd/validate")
    config.add_route("gkuser_users_of_role", "/gkuser/all/role/{userrole}")
    config.add_route("gkuser_uname", "/gkuser/check/{username}")
    config.add_route("gkuser_registration", "/gkuser/check_registration")

    # invite
    config.add_route("invite", "/invite")
    config.add_route("invite_accept", "/invite/accept")
    config.add_route("invite_reject", "/invite/reject")

    # login
    config.add_route("login_user", "/login/user")
    config.add_route("login_org", "/login/org")

    # product
    config.add_route("product", "/product")
    config.add_route("product_tax", "/product/tax")
    config.add_route("product_check_gst", "/product/check/gst")
    config.add_route("product_hsn", "/product/hsn")
    config.add_route("product_stock", "/product/stock")
    config.add_route("product_lastprice", "/product/lastprice")
    config.add_route("godown_product", "/godown/product/{productcode}")
    config.add_route("product_godown", "/product/godown/{godownid}")
    config.add_route("product_category", "/product/category/{categorycode}")
    config.add_route("product_productcode", "/product/{productcode}")

    # tax
    config.add_route("tax", "/tax")
    config.add_route("tax_search", "/tax/search/{pscflag}")
    config.add_route("tax_taxid", "/tax/{taxid}")

    # customer
    config.add_route("customer", "/customer")
    config.add_route(
        "customer_search_by_account", "/customer/search/account/{accountcode}"
    )
    config.add_route("customer_search_by_name", "/customer/search/name/{custname}")
    config.add_route("customer_custid", "/customer/{custid}")

    # invoice
    config.add_route("invoice", "/invoice")
    config.add_route("invoice_list", "/invoice/list")
    config.add_route("invoice_list_rectify", "/invoice/list/rectify")
    config.add_route("invoice_nonrejected", "/invoice/nonrejected")
    config.add_route("invoice_id", "/invoice/next_id")
    config.add_route("cashmemo", "/cashmemo")
    config.add_route("delnote_unbilled", "/delchal/unbilled")
    config.add_route("invoice_attachment", "/invoice/attachment/{invid}")
    config.add_route("invoice_cancel", "/invoice/cancel/{invid}")
    config.add_route("invoice_invid", "/invoice/{invid}")
    config.add_route("invoice_crdrid", "/invoice/drcr/{invid}")
    config.add_route("invoice_rnid", "/invoice/rnid/{invid}")

    # delchal
    config.add_route("delchal", "/delchal")
    config.add_route("delchal_attachment", "/delchal/attachment/{dcid}")
    config.add_route("delchal_cancel", "/delchal/cancel")
    config.add_route("delchal_last", "/delchal/last")
    config.add_route("delchal_next_id", "/delchal/next_id")
    config.add_route("delchal_dcid", "/delchal/{dcid}")
    config.add_route("delchal_cancel_dcid", "/delchal/cancel/{dcid}")
    config.add_route("delchal_invid", "/delchal/invid/{dcid}")

    config.add_route("budget", "/budget")
    config.add_route("categoryspecs", "/categoryspecs")
    config.add_route("orgyears", "/orgyears/{orgname}/{orgtype}")
    config.add_route("transaction", "/transaction")
    config.add_route("bankrecon", "/bankrecon")
    config.add_route("accounts", "/accounts")
    config.add_route("accounts-xlsx", "/accounts/spreadsheet")
    config.add_route("account", "/account/{accountcode}")
    config.add_route("account_details", "/account-details")
    config.add_route("projects", "/projects")
    config.add_route("project", "/project/{projectcode}")
    config.add_route("accountsbyrule", "/accountsbyrule")
    config.add_route("groupallsubgroup", "/groupallsubgroup/{groupcode}")
    config.add_route("groupsubgroup", "/groupsubgroup/{groupcode}")
    config.add_route("groupsubgroups", "/groupsubgroups")
    config.add_route("groups_subgroups", "/groups-subgroups")
    config.add_route("groupDetails", "/groupDetails/{groupcode}")
    config.add_route("close-books", "/closebooks")
    config.add_route("roll-over", "/rollover")
    config.add_route("rollclose", "/rollclose")
    config.add_route("forgotpassword", "/forgotpassword")
    config.add_route("categories", "/categories")
    config.add_route("godown", "/godown")
    config.add_route("bank", "/bank")
    config.add_route("purchaseorder", "/purchaseorder")
    config.add_route("transfernote", "/transfernote")
    config.add_route("discrepancynote", "/discrepancynote")
    config.add_route("log", "/log")
    config.add_route("logSort", "/log/dateRange")
    config.add_route("rejectionnote", "/rejectionnote")
    config.add_route("billwise", "/billwise")
    config.add_route("state", "/state")
    config.add_route("drcrnote", "/drcrnote")
    config.add_route("dashboard", "/dashboard")
    config.add_route("config", "/config")
    config.add_route("spreadsheet", "/spreadsheet")
    config.add_route("ifsc", "/ifsc")
    config.add_route("dev", "/dev")  # Comment in production
    config.add_route("hsn", "/hsn")
    # export org data
    config.add_route("export-json", "/export/json")
    config.add_route("export-xlsx", "/export/xlsx")
    # import org data
    config.add_route("import-organisation", "/import/organisation")
    config.add_route("overwrite-organisation", "/import/overwrite-organisation")
    config.add_route("import-xlsx", "/import/xlsx")

    config.add_route("index", "/")

    # reports
    config.add_route("product-register", "/reports/product-register")
    config.add_route("registers", "/reports/registers")
    config.add_route("profit-loss", "/reports/profit-loss")
    config.add_route("balance-sheet", "/reports/balance-sheet")
    config.add_route("gross-trial-balance", "/reports/trial-balance/gross")
    config.add_route("net-trial-balance", "/reports/trial-balance/net")
    config.add_route("extended-trial-balance", "/reports/trial-balance/extended")
    config.add_route("ledger-monthly", "/reports/ledger/monthly")
    config.add_route("ledger", "/reports/ledger")
    config.add_route("ledger-crdr", "/reports/ledger/crdr")
    config.add_route("godown-register", "/reports/godown-register/{goid}")
    config.add_route("cash-flow", "/reports/cash-flow")
    config.add_route("stock-report", "/reports/stock-report")
    config.add_route("stock-on-hand", "/reports/stock-on-hand")
    config.add_route("godown-stock-godownincharge", "/reports/godown-stock-godownincharge")
    config.add_route("godownwise-stock-value", "/reports/godownwise-stock-value")
    config.add_route("godownwise-stock-on-hand", "/reports/godownwise-stock-on-hand")
    config.add_route("category-wise-stock-on-hand", "/reports/category-wise-stock-on-hand")
    config.add_route("deleted-voucher", "/reports/deleted-voucher")
    config.add_route("project-statement", "/reports/project-statement")
    config.add_route("closing-balance", "/reports/closing-balance")
    config.add_route("log-statement", "/reports/log-statement")
    config.add_route("del-unbilled", "/reports/del-unbilled")
    config.add_route("gst-calc", "/reports/gst-calc")

    # WIP: v2 of profit loss report
    config.add_route("profit-loss-new", "/reports/v2/profit-loss")

    # reports spreadsheets
    config.add_route("product-register-xlsx", "/spreadsheet/product-register")
    config.add_route("view-register-xlsx", "/spreadsheet/view-register")
    config.add_route("profitloss-xlsx", "/spreadsheet/profit-loss")
    config.add_route("balance-sheet-xlsx", "/spreadsheet/balance-sheet")
    config.add_route("trial-balance-xlsx", "/spreadsheet/trial-balance")
    config.add_route("ledger-monthly-xlsx", "/spreadsheet/ledger/monthly")
    config.add_route("ledger-xlsx", "/spreadsheet/ledger")

    # Unit of measurement
    config.add_route("uom", "/unitofmeasurement")
    config.add_route("uom-single", "/unitofmeasurement/{uomid}")

    # GST returns
    config.add_route("gstr1", "/gst/returns/r1")
    config.add_route("gstr3b", "/gst/returns/3b")
    # GSTIN captcha validation
    config.add_route("gst-captcha", "/gst/captcha")
    # GST news
    config.add_route("gstnews", "/gst-news")

    # Add static file path
    config.add_static_view(name="spec", path="spec")
