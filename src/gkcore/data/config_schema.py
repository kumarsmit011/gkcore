from .enum import CONFIG_ENUM

payloadSchema1 = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "gkschema.payload1.json",
    "type": "object",
    "properties": {
        "config": {"type": "object"},
        "path": {"type": "array", "items": {"type": ["number", "string"]}},
    },
    "required": ["config"],
}

payloadSchema2 = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "gkschema.payload2.json",
    "type": "object",
    "properties": {
        "config": {"type": ["object", "array", "string", "number", "boolean"]},
        "path": {"type": "array", "items": {"type": ["number", "string"]}},
    },
    "required": ["config", "path"],
}

"""
 Reusable schema used in "create transaction" forms.
 The following schema elements that are booleans can also be objects that take boolean values.
 The schema has to be updated when a change occurs.
"""
transactionPageSchema = {
    "party": {
        "$id": "gkschema.transaction.party.json",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "type": {"type": "boolean"},
            "custid": {"type": "boolean"},
            "name": {
                "type": ["boolean", "object"],
                "additionalProperties": False,
                "properties": {"disabled": {"type": "boolean"}},
            },
            "addr": {"type": "boolean"},
            "state": {"type": "boolean"},
            "gstin": {"type": "boolean"},
            "tin": {"type": "boolean"},
            "pin": {"type": "boolean"},
            "options": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "states": {"type": "boolean"},
                    "gstin": {"type": "boolean"},
                },
            },
            "class": {
                "type": "object",
            },
        },
    },
    "ship": {
        "$id": "gkschema.transaction.ship.json",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "copyFlag": {"type": "boolean"},
            "name": {"type": "boolean"},
            "addr": {"type": "boolean"},
            "state": {"type": "boolean"},
            "gstin": {"type": "boolean"},
            "tin": {"type": "boolean"},
            "pin": {"type": "boolean"},
            "class": {
                "type": "object",
            },
        },
    },
    "bill": {
        "$id": "gkschema.transaction.bill.json",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "index": {"type": "boolean"},
            "product": {
                "type": ["boolean", "object"],
                "additionalProperties": False,
                "properties": {
                    "mobileMode": {
                        "type": ["boolean", "object"],
                        "properties": {"disabled": {"type": "boolean"}},
                    },
                    "addBtn": {"type": "boolean"},
                    "disabled": {"type": "boolean"},
                },
            },
            "hsn": {"type": "boolean"},
            "qty": {
                "type": ["boolean", "object"],
                "additionalProperties": False,
                "properties": {
                    "mobileMode": {
                        "type": ["boolean", "object"],
                        "properties": {"disabled": {"type": "boolean"}},
                    },
                    "checkStock": {"type": "boolean"},
                    "disabled": {"type": "boolean"},
                },
            },
            "fqty": {
                "type": ["boolean", "object"],
                "properties": {"disabled": {"type": "boolean"}},
            },
            "packageCount": {
                "type": ["boolean", "object"],
                "additionalProperties": False,
                "properties": {
                    "mobileMode": {
                        "type": ["boolean", "object"],
                        "properties": {"disabled": {"type": "boolean"}},
                    },
                },
            },
            "rate": {
                "type": ["boolean", "object"],
                "properties": {"disabled": {"type": "boolean"}},
            },
            "discount": {"type": "boolean"},
            "taxable": {"type": "boolean"},
            "cgst": {"type": "boolean"},
            "sgst": {"type": "boolean"},
            "igst": {"type": "boolean"},
            "cess": {"type": "boolean"},
            "vat": {"type": "boolean"},
            "rowSelected": {"type": "boolean"},
            "total": {
                "type": ["boolean", "object"],
                "additionalProperties": False,
                "properties": {
                    "mobileMode": {"type": "boolean"},
                },
            },
            "footer": {"type": "object"},
            "addBtn": {
                "type": ["boolean", "object"],
                "additionalProperties": False,
                "properties": {
                    "mobileMode": {"type": "boolean"},
                },
            },
            "editBtn": {
                "type": ["boolean", "object"],
                "additionalProperties": False,
                "properties": {
                    "mobileMode": {"type": "boolean"},
                },
            },
            "dcValue": {
                "type": ["boolean", "object"],
                "additionalProperties": False,
                "properties": {
                    "mobileMode": {
                        "type": ["boolean", "object"],
                        "properties": {"disabled": {"type": "boolean"}},
                    },
                },
            },
        },
    },
    "payment": {
        "$id": "gkschema.transaction.payment.json",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "mode": {"type": "boolean"},
            "bank": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "no": {"type": "boolean"},
                    "name": {"type": "boolean"},
                    "branch": {"type": "boolean"},
                    "ifsc": {"type": "boolean"},
                },
            },
            "class": {"type": "object"},
        },
    },
    "transport": {
        "$id": "gkschema.transaction.transport.json",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "packageCount": {"type": "boolean"},
            "mode": {"type": "boolean"},
            "vno": {"type": "boolean"},
            "date": {"type": "boolean"},
            "reverseCharge": {"type": "boolean"},
            "class": {"type": "object"},
        },
    },
    "total": {
        "$id": "gkschema.transaction.total.json",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "taxable": {"type": "boolean"},
            "discount": {"type": "boolean"},
            "vat": {"type": "boolean"},
            "igst": {"type": "boolean"},
            "cess": {"type": "boolean"},
            "roundOff": {"type": "boolean"},
            "value": {"type": "boolean"},
            "valueText": {"type": "boolean"},
        },
    },
    "comments": {
        "$id": "gkschema.transaction.comments.json",
        "type": "object",
        "additionalProperties": False,
        "properties": {"class": {"type": "object"}},
    },
}

transactionConfigSchema = {
    "$id": "gkschema.transaction.json",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        CONFIG_ENUM["PAGES"]["create-invoice"]: {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                CONFIG_ENUM["CONFIGS"]["page-layout"]: {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "type": {"type": "boolean"},
                        "taxType": {"type": "boolean"},
                        "inv": {
                            "type": "object",
                            "properties": {
                                "no": {"type": ["boolean", "object"]},
                                "date": {"type": "boolean"},
                                "delNote": {"type": ["boolean", "object"]},
                                "ebn": {"type": "boolean"},
                                "addr": {"type": "boolean"},
                                "pin": {"type": "boolean"},
                                "state": {"type": "boolean"},
                                "issuer": {"type": "boolean"},
                                "role": {"type": "boolean"},
                                "class": {"type": "object"},
                            },
                        },
                        "party": {"$ref": "gkschema.transaction.party.json#"},
                        "ship": {"$ref": "gkschema.transaction.ship.json#"},
                        "bill": {"$ref": "gkschema.transaction.bill.json#"},
                        "payment": {"$ref": "gkschema.transaction.payment.json#"},
                        "transport": {"$ref": "gkschema.transaction.transport.json#"},
                        "total": {"$ref": "gkschema.transaction.total.json#"},
                        "comments": {"$ref": "gkschema.transaction.comments.json#"},
                    },
                }
            },
        }
    },
}

transactionBaseSchema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "gkschema.transaction.base.json",
}

"""
 Schema for Global Config
"""
globalConfigSchema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "gkschema.global.json",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        CONFIG_ENUM["PAGES"]["global"]: {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                CONFIG_ENUM["CONFIGS"]["global"]: {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "general": {
                            "type": "object",
                        },
                        "transaction": {
                            "type": "object",
                        },
                    },
                }
            },
        }
    },
}

workflowConfigSchema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "gkschema.workflow.json",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        CONFIG_ENUM["PAGES"]["workflow-invoice"]: {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                CONFIG_ENUM["CONFIGS"]["workflow-left-pane-columns"]: {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {
                                "type": "string",
                                "enum": [
                                    "Date",
                                    "Customer",
                                    "Amount",
                                    "Inv No",
                                    "Tax",
                                ],
                            },
                            "key": {
                                "type": "string",
                                "enum": [
                                    "dateObj",
                                    "custname",
                                    "netamt",
                                    "invoiceno",
                                    "taxamt",
                                ],
                            },
                            "sortable": {"type": "boolean"},
                            "tdClass": {"type": ["string", "array"]},
                        },
                        "required": ["label", "key", "sortable"],
                    },
                }
            },
        },
        CONFIG_ENUM["PAGES"]["workflow-dc-note"]: {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                CONFIG_ENUM["CONFIGS"]["workflow-left-pane-columns"]: {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {
                                "type": "string",
                                "enum": [
                                    "Date",
                                    "Customer",
                                    "Amount",
                                    "No",
                                ],
                            },
                            "key": {
                                "type": "string",
                                "enum": [
                                    "dateObj",
                                    "custname",
                                    "totreduct",
                                    "drcrno",
                                ],
                            },
                            "sortable": {"type": "boolean"},
                            "tdClass": {"type": ["string", "array"]},
                        },
                        "required": ["label", "key", "sortable"],
                    },
                }
            },
        },
        CONFIG_ENUM["PAGES"]["workflow-cash-memo"]: {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                CONFIG_ENUM["CONFIGS"]["workflow-left-pane-columns"]: {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {
                                "type": "string",
                                "enum": [
                                    "Date",
                                    "Amount",
                                    "No",
                                ],
                            },
                            "key": {
                                "type": "string",
                                "enum": [
                                    "dateObj",
                                    "invoicetotal",
                                    "invoiceno",
                                ],
                            },
                            "sortable": {"type": "boolean"},
                            "tdClass": {"type": ["string", "array"]},
                        },
                        "required": ["label", "key", "sortable"],
                    },
                }
            },
        },
        CONFIG_ENUM["PAGES"]["workflow-cash-memo"]: {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                CONFIG_ENUM["CONFIGS"]["workflow-left-pane-columns"]: {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {
                                "type": "string",
                                "enum": [
                                    "Date",
                                    "Amount",
                                    "No",
                                ],
                            },
                            "key": {
                                "type": "string",
                                "enum": [
                                    "dateObj",
                                    "invoicetotal",
                                    "invoiceno",
                                ],
                            },
                            "sortable": {"type": "boolean"},
                            "tdClass": {"type": ["string", "array"]},
                        },
                        "required": ["label", "key", "sortable"],
                    },
                }
            },
        },
        CONFIG_ENUM["PAGES"]["workflow-delivery-note"]: {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                CONFIG_ENUM["CONFIGS"]["workflow-left-pane-columns"]: {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {
                                "type": "string",
                                "enum": [
                                    "Date",
                                    "Name",
                                    "No",
                                    "Godown",
                                    "Delivery Type",
                                ],
                            },
                            "key": {
                                "type": "string",
                                "enum": [
                                    "dateObj",
                                    "custname",
                                    "dcno",
                                    "goname",
                                    "dcflag",
                                ],
                            },
                            "sortable": {"type": "boolean"},
                            "tdClass": {"type": ["string", "array"]},
                        },
                        "required": ["label", "key", "sortable"],
                    },
                }
            },
        },
        CONFIG_ENUM["PAGES"]["workflow-ps-order"]: {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                CONFIG_ENUM["CONFIGS"]["workflow-left-pane-columns"]: {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {
                                "type": "string",
                                "enum": [
                                    "Date",
                                    "Customer",
                                    "Amount",
                                    "No",
                                ],
                            },
                            "key": {
                                "type": "string",
                                "enum": [
                                    "dateObj",
                                    "customer",
                                    "ordertotal",
                                    "orderno",
                                ],
                            },
                            "sortable": {"type": "boolean"},
                            "tdClass": {"type": ["string", "array"]},
                        },
                        "required": ["label", "key", "sortable"],
                    },
                }
            },
        },
        CONFIG_ENUM["PAGES"]["workflow-rejection-note"]: {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                CONFIG_ENUM["CONFIGS"]["workflow-left-pane-columns"]: {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {
                                "type": "string",
                                "enum": [
                                    "Date",
                                    "Amount",
                                    "Inv No",
                                    "No",
                                ],
                            },
                            "key": {
                                "type": "string",
                                "enum": [
                                    "dateObj",
                                    "rntotal",
                                    "invoiceno",
                                    "rnno",
                                ],
                            },
                            "sortable": {"type": "boolean"},
                            "tdClass": {"type": ["string", "array"]},
                        },
                        "required": ["label", "key", "sortable"],
                    },
                }
            },
        },
        CONFIG_ENUM["PAGES"]["workflow-transfer-note"]: {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                CONFIG_ENUM["CONFIGS"]["workflow-left-pane-columns"]: {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {
                                "type": "string",
                                "enum": [
                                    "Date",
                                    "No",
                                ],
                            },
                            "key": {
                                "type": "string",
                                "enum": [
                                    "dateObj",
                                    "transfernoteno",
                                ],
                            },
                            "sortable": {"type": "boolean"},
                            "tdClass": {"type": ["string", "array"]},
                        },
                        "required": ["label", "key", "sortable"],
                    },
                }
            },
        },
        CONFIG_ENUM["PAGES"]["workflow-voucher"]: {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                CONFIG_ENUM["CONFIGS"]["workflow-left-pane-columns"]: {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {
                                "type": "string",
                                "enum": [
                                    "Date",
                                    "Dr",
                                    "Cr",
                                    "Type",
                                    "No",
                                    "Narration",
                                ],
                            },
                            "key": {
                                "type": "string",
                                "enum": [
                                    "dateObj",
                                    "drAmount",
                                    "crAmount",
                                    "vouchertype",
                                    "vouchernumber",
                                    "narration",
                                ],
                            },
                            "sortable": {"type": "boolean"},
                            "tdClass": {"type": ["string", "array"]},
                        },
                        "required": ["label", "key", "sortable"],
                    },
                }
            },
        },
        CONFIG_ENUM["PAGES"]["workflow-business"]: {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                CONFIG_ENUM["CONFIGS"]["workflow-left-pane-columns"]: {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {
                                "type": "string",
                                "enum": [
                                    "Name",
                                ],
                            },
                            "key": {
                                "type": "string",
                                "enum": [
                                    "productdesc",
                                ],
                            },
                            "sortable": {"type": "boolean"},
                            "tdClass": {"type": ["string", "array"]},
                        },
                        "required": ["label", "key", "sortable"],
                    },
                }
            },
        },
        CONFIG_ENUM["PAGES"]["workflow-contacts"]: {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                CONFIG_ENUM["CONFIGS"]["workflow-left-pane-columns"]: {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {
                                "type": "string",
                                "enum": [
                                    "Name",
                                ],
                            },
                            "key": {
                                "type": "string",
                                "enum": [
                                    "custname",
                                ],
                            },
                            "sortable": {"type": "boolean"},
                            "tdClass": {"type": ["string", "array"]},
                        },
                        "required": ["label", "key", "sortable"],
                    },
                }
            },
        },
    },
}
