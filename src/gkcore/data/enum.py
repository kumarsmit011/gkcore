STATUS_CODES = {
    "Success": 0,
    "DuplicateEntry": 1,
    "UnauthorisedAccess": 2,
    "ConnectionFailed": 3,
    "BadPrivilege": 4,
    "ActionDisallowed": 5,
    "ProxyServerError": 6,
    "ValidationError": 7,
}

GST_REG_TYPE = {
    "unregistered": 0,
    "consumer": 1,
    "regular": 2,
    "composition": 3,
}

GST_PARTY_TYPE = {
    "deemed_export": 0,
    "sez": 1,
    "overseas": 2,
    "uin_holders": 3,
}

DR_CR_MODE = {
    "discount": 4,
    "returns": 18,
    "service_deficiency": 10,
    "inv_correction": 11,
    "pos_change": 12,
    "prov_assessment": 13,
    "others": 14,
}

# Enum for keys used in Config JSON objects

CONFIG_ENUM = {
    "PAGES": {
        "global": 0,
        "workflow": 10,
        "workflow-invoice": 20,
        "workflow-dc-note": 30,
        "workflow-cash-memo": 40,
        "workflow-delivery-note": 50,
        "workflow-ps-order": 60,
        "workflow-rejection-note": 70,
        "workflow-transfer-note": 80,
        "workflow-voucher": 90,
        "workflow-business": 100,
        "workflow-contacts": 110,
        "create-invoice": 120,
    },
    "CONFIGS": {"global": 0, "workflow-left-pane-columns": 11, "page-layout": 121},
}
