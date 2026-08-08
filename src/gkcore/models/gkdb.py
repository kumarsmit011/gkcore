"""
Copyright (C) 2013, 2014, 2015, 2016 Digital Freedom Foundation
Copyright (C) 2017, 2018, 2019, 2020 Digital Freedom Foundation & Accion Labs Pvt. Ltd.
  This file is part of GNUKhata:A modular,robust and Free Accounting System.

  GNUKhata is Free Software; you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as
  published by the Free Software Foundation; either version 3 of
  the License, or (at your option) any later version.

  GNUKhata is distributed in the hope that it will be useful, but
  WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public
  License along with GNUKhata (COPYING); if not, write to the
  Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
  Boston, MA  02110-1301  USA59 Temple Place, Suite 330,


Contributors:
"Krishnakant Mane" <kk@gmail.com>
"""
import os
from sqlalchemy.dialects.postgresql.json import JSONB

"""
This module contains the sqlalchemy expression based table definitions.
They will be converted to real sql statements and tables will be subsequently created by create_all function in initdb.py.
"""
import datetime
from sqlalchemy.dialects.postgresql import JSONB, JSON

from sqlalchemy import (
    Table,
    Column,
    Index,
    Integer,
    Text,
    Unicode,  # <- will provide Unicode field
    UnicodeText,  # <- will provide Unicode text field
    DateTime,
    Date,
    Float
    # <- time abstraction field
)
from sqlalchemy.sql.schema import ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.sql.sqltypes import BOOLEAN, Numeric, UnicodeText, Integer
from sqlalchemy import MetaData

# Get maximum file upload size limit from env variable
# If not set, fall back to 1MB
MAX_UPLOAD_SIZE = os.environ.get("GKCORE_MAX_UPLOAD_SIZE") or 1048576

# metadata is the module that converts Python code into real sql statements, specially for creating tables.
metadata = MetaData()
""" table for secret code that is used to decode json objects.
This will be generated during the database setup.
"""
signature = Table(
    "signature",
    metadata,
    Column("secretcode", UnicodeText),
)


"""
This table is for storing state information.  
A state will have its corresponding code with name.
"""
state = Table(
    "state",
    metadata,
    Column("statecode", Integer, primary_key=True),
    Column("statename", UnicodeText),
    Column("abbreviation", UnicodeText),
)

""" organisation table for saving basic details including type, financial year start and end, flags for roll over and close books.
Also stores other details like the pan or sales tax number.
bankdetails is a dictionary will have bankname,accountno., branchname and ifsccode
Every time a new organisation is created or recreated for it's new financial year, a new record is added.
Besides the personal details, we also have some flags determining the preferences.
ivflag = inventory flag , billflag = billwise accounting , invsflag = invoicing,
maflag = multiple accounts for products and avflag = automatic vouchers for invoices.
modeflag=0 old interface for payment and receipt voucher is used.
modeflag=1 new user friendly interface for payment and receipt voucher is used.
users -> a list of users that are part of that org. Stored as JSONB so that we can quickly check if a userid is within that column

orgconf Format:
{
    page_id: {
        config_id: {
            config
        }
    }
}

page_id and config_id will be stored in client side as enums.

users Format:
{
    userid: invitestatus (true/false)
}
"""
organisation = Table(
    "organisation",
    metadata,
    Column("orgcode", Integer, primary_key=True),
    Column("orgname", UnicodeText, nullable=False),
    Column("orgtype", UnicodeText, nullable=False),
    Column("yearstart", Date, nullable=False),
    Column("yearend", Date, nullable=False),
    Column("orgcity", UnicodeText),
    Column("orgaddr", UnicodeText),
    Column("orgpincode", Unicode(30)),
    Column("orgstate", UnicodeText, nullable=False),
    Column("orgcountry", UnicodeText),
    Column("orgtelno", UnicodeText),
    Column("orgfax", UnicodeText),
    Column("orgwebsite", UnicodeText),
    Column("orgemail", UnicodeText),
    Column("orgpan", UnicodeText),
    Column("orgmvat", UnicodeText),
    Column("orgstax", UnicodeText),
    Column("orgregno", UnicodeText),
    Column("orgregdate", UnicodeText),
    Column("orgfcrano", UnicodeText),
    Column("orgfcradate", UnicodeText),
    Column("orgconf", JSONB, default="{}"),
    Column("roflag", Integer, default=0),
    Column("booksclosedflag", Integer, default=0),
    Column("invflag", Integer, default=0),
    Column("billflag", Integer, default=1),
    Column("invsflag", Integer, default=1),
    Column("avflag", Integer, default=1),
    Column("maflag", Integer, default=1),
    Column("modeflag", Integer, default=1),
    Column("avnoflag", Integer, default=0),
    Column("ainvnoflag", Integer, default=0),
    Column("logo", JSON, CheckConstraint("length(logo::text) <= %d" % (MAX_UPLOAD_SIZE), name="check_logo_size")),
    Column("gstin", JSONB),
    Column("tin", UnicodeText),
    Column("cin", UnicodeText),
    Column("users", JSONB),
    Column("bankdetails", JSON),
    UniqueConstraint("orgname", "orgtype", "yearstart"),
    UniqueConstraint("orgname", "orgtype", "yearend"),
    Index("orgindex", "orgname", "yearstart", "yearend"),
    info={"key_related_json_fields": {"users": "gkusers"}},
)

""" the table for groups and subgroups.
Note that the groupcode is used as an internal (self referencing) foreign key named subgroupof.
So every group is either a parent group or subgroup who will have the groupcode as foreign key in subgroup off to which this subgroup belongs.This essentially means a group can be a subgroup of a parent group who's groupcode is in it's subgroupof field."""

groupsubgroups = Table(
    "groupsubgroups",
    metadata,
    Column("groupcode", Integer, primary_key=True),
    Column("groupname", UnicodeText, nullable=False),
    Column(
        "subgroupof",
        Integer,
        ForeignKey("groupsubgroups.groupcode", ondelete="CASCADE"),
        nullable=True,
    ),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("orgcode", "groupname"),
    Index("grpindex", "orgcode", "groupname"),
)
"""
table for categories and subcategories.
This table is for storing names of categories and their optional one or many subcategories.
Note that subcategory might have it's own subcategories and so on.
The way we achieve this multi level tree is by having categorycode which is primary key of the table.
Now this key becomes foreign key in the same table under the name subcategoryof.
So if a category has a value in subcategoryof wich matches another categorycode, then that category becomes the subcategory.
"""

categorysubcategories = Table(
    "categorysubcategories",
    metadata,
    Column("categorycode", Integer, primary_key=True),
    Column("categoryname", UnicodeText, nullable=False),
    Column(
        "subcategoryof",
        Integer,
        ForeignKey("categorysubcategories.categorycode", ondelete="CASCADE"),
        nullable=True,
    ),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("orgcode", "categoryname"),
    Index("catindex", "orgcode", "categoryname"),
)
"""
This is the table for maintaining the ontology.
Once you have defined the name of category,this table will store the attributes of that category, as in what features are there.
this table not just stores the list of attributes of the category, but also the type, as in text, number, true false etc.
Needless to say that the categorycode becomes a foreign key here.
The type will be an enum, eg. 0= number, 1=text etc.
"""
categoryspecs = Table(
    "categoryspecs",
    metadata,
    Column("spcode", Integer, primary_key=True),
    Column("attrname", UnicodeText, nullable=False),
    Column("attrtype", Integer, nullable=False),
    Column("productcount", Integer, default=0),
    Column(
        "categorycode",
        Integer,
        ForeignKey("categorysubcategories.categorycode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("categorycode", "attrname"),
    Index("catspecindex", "orgcode", "attrname"),
)
"""
This table is for unit of measurement for products.
The unit of measurement has units, conversion rates and its resulting unit.
sysunit state that unit is system generated or not. for system generated units sysunit is 1 and user created units sysunit is 0. 
subunitof - to create parent-child relationship
uqc - to map appropriate GST valid uqc

"""
unitofmeasurement = Table(
    "unitofmeasurement",
    metadata,
    Column("uomid", Integer, primary_key=True),
    Column("unitname", UnicodeText, nullable=False),
    Column("description", UnicodeText),
    Column("conversionrate", Numeric(13, 2), default=0.00),
    Column(
        "subunitof",
        Integer,
        ForeignKey("unitofmeasurement.uomid", ondelete="CASCADE"),
        nullable=True,
    ),
    Column("uqc", Integer),
    Column("frequency", Integer),
    Column("sysunit", Integer, default=0),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=True,
    ),
    UniqueConstraint("unitname", "orgcode"),
    Index("unitofmeasurement_frequency", "frequency"),
    Index("unitofmeasurement_unitname", "unitname"),
    Index("unitofmeasurement_orgcode", "orgcode"),
)
"""
This table is for product, based on a certain category.
The products are stored on the basis of the selected category and must have data exactly matching the attributes or properties as one may call it.
The table is having a json field which has the keys matching the attributes from the spects table for a certain category.
gscode is to store HSN code or accounting service code, gsflag is 7 for goods and 19 for service . 
1 organisation cannot have same products.
"""
product = Table(
    "product",
    metadata,
    Column("productcode", Integer, primary_key=True),
    Column("gscode", UnicodeText),
    Column("gsflag", Integer, nullable=False),
    Column("percentdiscount", Numeric(5, 2), default=0.00),
    Column("amountdiscount", Numeric(13, 2), default=0.00),
    Column("productdesc", UnicodeText, nullable=False),
    Column("openingstock", Numeric(13, 2), default=0.00),
    Column("specs", JSONB),
    Column(
        "categorycode",
        Integer,
        ForeignKey("categorysubcategories.categorycode", ondelete="CASCADE"),
    ),
    Column("uomid", Integer, ForeignKey("unitofmeasurement.uomid", ondelete="CASCADE")),
    Column("prodsp", Numeric(13, 2)),
    Column("prodmrp", Numeric(13, 2)),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("categorycode", "productdesc"),
    UniqueConstraint("productdesc", "orgcode"),
    Index("product_orgcodeindex", "orgcode"),
    Index("product_categorycode", "categorycode"),
)
"""
Table for customers and suppliers.
We need this data when we sell goods or service.
Also when we purchase the same.
The reason to store this data is that we may need it in both invoice and delivery chalan.
Here the csflag is 3 for customer and 19 for supplier
gstin to store unique code of cust/supp for gst for every state (json)
Bankdetails is a dictionary will have bankname,accountno., branchname and ifsccode.
Check enum.py for possible values for "gst_reg_type" and "gst_party_type"
"""
customerandsupplier = Table(
    "customerandsupplier",
    metadata,
    Column("custid", Integer, primary_key=True),
    Column("custname", UnicodeText, nullable=False),
    Column("gstin", JSONB),
    Column("gst_reg_type", Integer),
    Column("gst_party_type", Integer),
    Column("tin", UnicodeText),
    Column("custaddr", UnicodeText),
    Column("pincode", UnicodeText),
    Column("custphone", UnicodeText),
    Column("custemail", UnicodeText),
    Column("custfax", UnicodeText),
    Column("custpan", UnicodeText),
    Column("custtan", UnicodeText),
    Column("custdoc", JSONB),
    Column("state", UnicodeText),
    Column("country", UnicodeText),
    Column("csflag", Integer, nullable=False),
    Column("bankdetails", JSONB),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("orgcode", "custname"),
    UniqueConstraint("orgcode", "custemail"),
    UniqueConstraint("orgcode", "custpan"),
    UniqueConstraint("orgcode", "custtan"),
    UniqueConstraint("orgcode", "gstin"),
    UniqueConstraint("orgcode", "tin"),
    Index("customer_supplier_orgcodeindex", "orgcode"),
)
"""
This Table stores last selling price of a product for a specific customer.
Fields productcode, custid and orgcode are foreign keys refering to corresponding fields in
product, customerandsupplier and organisation tables.
Inoutflag indicates whether it is a selling price(15) or purchase price(9).
Unique Constraint is used to prevent repeated entry for last price of same inoutflag of a product for the same customer
or supplier of the same organisation.
"""
cslastprice = Table(
    "cslastprice",
    metadata,
    Column("cslpid", Integer, primary_key=True),
    Column(
        "custid",
        Integer,
        ForeignKey("customerandsupplier.custid", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "productcode",
        Integer,
        ForeignKey("product.productcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("inoutflag", Integer),
    Column("lastprice", Numeric(13, 2), default=0.00),
    UniqueConstraint("orgcode", "custid", "productcode", "inoutflag"),
)
""" table to store accounts.
Every account belongs to either a group or subgroup.
For one organisation in a single financial year, an account name can never be duplicated.
So it has  2 foreign keys, first the orgcode of the organisation to which it belongs, secondly
the groupcode to with it belongs.
defaultflag is for setting the account as default for certain transactions.
so defaultflag will be '2' is for default bank transaction , '3' default for Cash, '16' is for Purchase and '19' is for sale.
"""

accounts = Table(
    "accounts",
    metadata,
    Column("accountcode", Integer, primary_key=True),
    Column("accountname", UnicodeText, nullable=False),
    Column(
        "groupcode", Integer, ForeignKey("groupsubgroups.groupcode"), nullable=False
    ),
    Column("openingbal", Numeric(13, 2), default=0.00),
    Column("vouchercount", Integer, default=0),
    Column("sysaccount", Integer, default=0),
    Column("defaultflag", Integer, default=0),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("orgcode", "accountname"),
    Index("accindex", "orgcode", "accountname"),
)
""" table for storing projects for one organisation.
This means that it has one foreign key, namely the org code of the organisation to which it belongs. """
projects = Table(
    "projects",
    metadata,
    Column("projectcode", Integer, primary_key=True),
    Column("projectname", UnicodeText, nullable=False),
    Column("sanctionedamount", Numeric(13, 2), default=0.00),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("orgcode", "projectname"),
)
""" table to store vouchers.
This table has one foreign key from organisation to which it belongs and has the project code to which it belongs.
Additionally this table has 2 json fields named Drs and Crs.
These are the fields which actually store the dr or cr amounts which their respective account codes of the accounts which are used in those transactions.
Key is the account code and value is the amount.
This helps us to store multiple Drs and Crs because there can be many key-value pares in the dictionary field.
Apart from this orgcode is there as the foreign key.  We also connect the invoice table where sales or purchase happens.  So there is a nullable foreign key here. """
vouchers = Table(
    "vouchers",
    metadata,
    Column("vouchercode", Integer, primary_key=True),
    Column("vouchernumber", UnicodeText, nullable=False),
    Column("voucherdate", DateTime, nullable=False),
    Column(
        "entrydate", DateTime, nullable=False, default=datetime.datetime.now().date()
    ),
    Column("narration", UnicodeText),
    Column("drs", JSONB, nullable=False),
    Column("crs", JSONB, nullable=False),
    Column("prjdrs", JSONB),
    Column("prjcrs", JSONB),
    Column("attachment", JSON, CheckConstraint("length(attachment::text) <= %d" % (MAX_UPLOAD_SIZE), name="check_attachment_size")),
    Column("attachmentcount", Integer, default=0),
    Column("vouchertype", UnicodeText, nullable=False),
    Column("lockflag", BOOLEAN, default=False),
    Column("delflag", BOOLEAN, default=False),
    Column("projectcode", Integer, ForeignKey("projects.projectcode")),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("invid", Integer, ForeignKey("invoice.invid")),
    Column("drcrid", Integer, ForeignKey("drcr.drcrid")),
    Column("instrumentno", UnicodeText),
    Column("bankname", UnicodeText),
    Column("branchname", UnicodeText),
    Column("instrumentdate", DateTime),
    Index("voucher_orgcodeindex", "orgcode"),
    Index("voucher_entrydate", "entrydate"),
    Index("voucher_vno", "vouchernumber"),
    Index("voucher_vdate", "voucherdate"),
    info={"key_related_json_fields": {"drs": "accounts", "crs": "accounts"}},
)

"""
Table for storing immutable details of transactions. The following tables represent
different types of transactions at the time of writing:
- invoice (Both Invoices and Cash Memos)
- delchal (Delivery Notes)
- drcr (Debit/Credit Notes)
- transfernote (Tranfer Notes)
- purchaseorder (Purchase/Sales Orders).
The `transaction_details` field of this table will store the transaction related
details in textual form in addition to their IDs so that even if those details,
like that of customers or products, change in future the data in the transaction
records remain unchanged. This is necessary to keep the transaction records
immutable.

Sample structure of `transaction_details` JSONB field:
{
    "godown": {
        // Same as the godown table structure
        "goid": 1,
        "goname": "Primary Godown",
        "state": "Kerala",
        "gocontact": "9876543210", // Phone number
        "contactname": "Jane Doe", // Name of the contact person
        "designation": "Godown Manager", // Designation of the contact person
        "orgcode": 1
    },
    "contact": {
        // Same as the customerandsupplier table structure
        "custid": 1,
        "custname": "Retail Customer",
        "gstin": { // JSONB with state code as key and GSTIN as value
            "22": "22AAAAA0000A1Z5"
        },
        "gst_reg_type": 0, // Check enum.py for possible values
        "gst_party_type": 0, // Check enum.py for possible values
        "tin": "22XXXXC0001",
        "custaddr": "Primary Address",
        "pincode": "495115",
        "custphone": "9876543211",
        "custemail": "customer@example.com",
        "custfax": "1234567890",
        "custpan": "AAAAA0000A",
        "custtan": "AAAA00000A",
        "state": "Chattisgarh",
        "country": "India",
        "csflag": 3, // 3 -> Customer, 19 -> Supplier
        "bankdetails": {
            "ifsc": "ABCD1234567",
            "accountno": "00123456789",
            "branchname": "Raipur"
        },
        "orgcode": 1
    },
    "products": {
        // Object with product ID as key
        "1": {
            "productcode": 1,
            "productdesc": "Pencil", // Name of product/service
            "gscode": {
                "hsn_code": 9609,
                "hsn_desc": "Pencils"
            }
        }
    },
    "godowns": {
        // Object with godown ID as key (only applicable for transfer notes).
        "1": {
            from_godown_details // Same as the godown structure above
        },
        "2": {
            to_godown_details // Same as the godown structure above
        }
     }
}
"""
transaction = Table(
    "transaction",
    metadata,
    Column("transaction_id", Integer, primary_key=True),
    Column("transaction_details", JSONB),
)

"""
Table for storing invoice records.
Every row represents one invoice.
taxflag states which tax is applied to products/services. Default value is set as 22 for VAT and if it is GST 7 will be set as taxflag.
Apart from the number and date, we also have a json field called contents.
This field is a nested dictionary.
The key of this field is the productcode while value is another dictionary.
This has a key as price per unit (ppu) and value as quantity (qty).
Note that invoice is connected to a voucher.
So the accounting part is thus connected with stock movement of that cost.
A new json field called freeqty.
Consignee (shipped to) is a json field which has name , address, state, statecode,gstin as keys along with its value.
Bankdetails is a dictionary will have bankname,accountno., branchname and ifsccode.
taxstate is a destination sate.
sourcestate is source state from where invoice is initiated.
Structure of a tax field is {productcode:taxrate}
save orgstategstin of sourcestate for organisation.
paymentmode states that Mode of payment i.e 'bank' or 'cash'. Default value is set as 2 for 'bank' and 3 for 'cash'.
inoutflag states that invoice 'in' or 'out' (i.e 9 for 'in' and 15 for 'out') 
Roundoff field is to check wheather invoice total is rounded off or not. 
0 = no round off 1 = invoice total amount rounded off.
discflag is used to check whether discount is in percent or in amount
1 = discount in amount, 16 = discount in percent.
"""
invoice = Table(
    "invoice",
    metadata,
    Column("invid", Integer, primary_key=True),
    Column("invoiceno", UnicodeText, nullable=False),
    Column("ewaybillno", UnicodeText),
    Column("invoicedate", DateTime, nullable=False),
    Column("supinvno", UnicodeText),
    Column("supinvdate", DateTime),
    Column("invnarration", UnicodeText),
    Column("taxflag", Integer, default=22),
    Column("contents", JSONB),
    Column("issuername", UnicodeText),
    Column("designation", UnicodeText),
    Column("tax", JSONB),
    Column("cess", JSONB),
    Column("amountpaid", Numeric(13, 2), default=0.00),
    Column("invoicetotal", Numeric(13, 2), nullable=False),
    Column("icflag", Integer, default=9),
    Column("roundoffflag", Integer, default=0),
    Column("discflag", Integer, default=1),
    Column("taxstate", UnicodeText),
    Column("sourcestate", UnicodeText),
    Column("orgstategstin", UnicodeText),
    Column("attachment", JSON, CheckConstraint("length(attachment::text) <= %d" % (MAX_UPLOAD_SIZE), name="check_attachment_size")),
    Column("attachmentcount", Integer, default=0),
    Column("orderid", Integer, ForeignKey("purchaseorder.orderid")),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("custid", Integer, ForeignKey("customerandsupplier.custid")),
    Column("consignee", JSONB),
    Column("freeqty", JSONB),
    Column("reversecharge", UnicodeText),
    Column("bankdetails", JSONB),
    Column("transportationmode", UnicodeText),
    Column("vehicleno", UnicodeText),
    Column("dateofsupply", DateTime),
    Column("discount", JSONB),
    Column("paymentmode", Integer, default=2),
    Column("address", UnicodeText),
    Column("pincode", UnicodeText),
    Column("inoutflag", Integer),
    Column("invoicetotalword", UnicodeText),
    Column("immutable_data_id", Integer, ForeignKey("transaction.transaction_id")),
    UniqueConstraint("orgcode", "invoiceno", name="invoice_orgcode_invoiceno_key"),
    Index("invoice_orgcodeindex", "orgcode"),
    Index("invoice_invoicenoindex", "invoiceno"),
    info={
        "key_related_json_fields": {
            "contents": "product",
            "tax": "product",
            "cess": "product",
            "freeqty": "product",
            "discount": "product"
        }
    },
)
billwise = Table(
    "billwise",
    metadata,
    Column("billid", Integer, primary_key=True),
    Column("vouchercode", Integer, ForeignKey("vouchers.vouchercode"), nullable=False),
    Column("invid", Integer, ForeignKey("invoice.invid"), nullable=False),
    Column("adjdate", DateTime),
    Column("adjamount", Numeric(12, 2), nullable=False),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
)
"""
This is the table which acts as a bin for canceled invoices.
While these invoices canceled, they are for investigation purpose if need be.
discflag is used to check whether discount is in percent or in amount
1 = discount in amount, 16 = discount in percent.
"""
invoicebin = Table(
    "invoicebin",
    metadata,
    Column("invid", Integer, primary_key=True),
    Column("invoiceno", UnicodeText, nullable=False),
    Column("invoicedate", DateTime, nullable=False),
    Column("taxflag", Integer, default=22),
    Column("contents", JSONB),
    Column("issuername", UnicodeText),
    Column("designation", UnicodeText),
    Column("tax", JSONB),
    Column("cess", JSONB),
    Column("amountpaid", Numeric(13, 2), default=0.00),
    Column("invoicetotal", Numeric(13, 2), nullable=False),
    Column("icflag", Integer, default=9),
    Column("discflag", Integer, default=1),
    Column("taxstate", UnicodeText),
    Column("sourcestate", UnicodeText),
    Column("orgstategstin", UnicodeText),
    Column("attachment", JSON, CheckConstraint("length(attachment::text) <= %d" % (MAX_UPLOAD_SIZE), name="check_attachment_size")),
    Column("attachmentcount", Integer, default=0),
    Column("orderid", Integer, ForeignKey("purchaseorder.orderid")),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("custid", Integer, ForeignKey("customerandsupplier.custid")),
    Column("consignee", JSONB),
    Column("freeqty", JSONB),
    Column("reversecharge", UnicodeText),
    Column("bankdetails", JSONB),
    Column("transportationmode", UnicodeText),
    Column("vehicleno", UnicodeText),
    Column("dateofsupply", DateTime),
    Column("discount", JSONB),
    Column("paymentmode", Integer, default=2),
    Column("address", UnicodeText),
    Column("pincode", UnicodeText),
    Column("inoutflag", Integer),
    Column("invoicetotalword", UnicodeText),
    Column("invnarration", UnicodeText),
    Column("dcinfo", JSONB),
    Column("immutable_data_id", Integer, ForeignKey("transaction.transaction_id")),
    Index("invoicebin_orgcodeindex", "orgcode"),
    Index("invoicebin_invoicenoindex", "invoiceno"),
    info={
        "key_related_json_fields": {
            "contents": "product",
            "tax": "product",
            "cess": "product",
            "freeqty": "product",
            "discount": "product"
        }
    },
)

"""
Table for challan.
This table stores the delivary challans issues when the goods move out.
This is generally done when payment is due.
The invoice table and this table will be linked in a subsequent table.
This is done because one invoice may have several dc's attached and for one dc may have several invoices.
In a situation where x items have been shipped against a dc, the customer approves only x -2, so the invoice against this dc will have x -2 items.
Another invoice may be issued if the remaining two items are approved by the customer.
dcflag is used for type of transaction: 1 - Approval, 2 - consignment, 3 - Free Replacement, etc.
taxflag states which tax is applied to products/services. Default value is set as 22 for VAT and for GST 7 will be set as taxflag.
Also we have json field called 'contents' which is nested dictionary.
The key of this field is the 'productcode' while value is another dictionary.
This has a key as price per unit (ppu) and value as quantity (qty).
Roundoff field is to check wheather delivery chalan total is rounded off or not. 
0 = no round off 1 = total amount rounded off.
discflag is used to check whether discount is in percent or in amount
1 = discount in amount, 16 = discount in percent.
"""
delchal = Table(
    "delchal",
    metadata,
    Column("dcid", Integer, primary_key=True),
    Column("dcno", UnicodeText, nullable=False),
    Column("dcdate", DateTime, nullable=False),
    Column("dcflag", Integer, nullable=False),
    Column("taxflag", Integer, default=7),
    Column("contents", JSONB),
    Column("tax", JSONB),
    Column("cess", JSONB),
    Column("issuername", UnicodeText),
    Column("designation", UnicodeText),
    Column("cancelflag", Integer, default=0),
    Column("canceldate", DateTime),
    Column("noofpackages", Integer),
    Column("modeoftransport", UnicodeText),
    Column("attachment", JSON, CheckConstraint("length(attachment::text) <= %d" % (MAX_UPLOAD_SIZE), name="check_attachment_size")),
    Column("consignee", JSONB),
    Column("taxstate", UnicodeText),
    Column("sourcestate", UnicodeText),
    Column("orgstategstin", UnicodeText),
    Column("freeqty", JSONB),
    Column("discount", JSONB),
    Column("vehicleno", UnicodeText),
    Column("dateofsupply", DateTime),
    Column("delchaltotal", Numeric(13, 2), nullable=False),
    Column("attachmentcount", Integer, default=0),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("custid", Integer, ForeignKey("customerandsupplier.custid")),
    Column("orderid", Integer, ForeignKey("purchaseorder.orderid", ondelete="CASCADE")),
    Column("inoutflag", Integer, nullable=False),
    Column("dcnarration", UnicodeText),
    Column("roundoffflag", Integer, default=0),
    Column("discflag", Integer, default=1),
    Column("totalinword", UnicodeText),
    UniqueConstraint("orgcode", "dcno", "custid"),
    Index("delchal_orgcodeindex", "orgcode"),
    Index("delchal_dcnoindex", "dcno"),
    info={
        "key_related_json_fields": {
            "contents": "product",
            "tax": "product",
            "cess": "product",
            "freeqty": "product",
            "discount": "product"
        }
    },
)
"""
This is the table which acts as a bin for cancelled delivery notes.
While these delivery notes cancelled, they are for investigation purpose if need be.
"""

delchalbin = Table(
    "delchalbin",
    metadata,
    Column("dcid", Integer, primary_key=True),
    Column("dcno", UnicodeText, nullable=False),
    Column("dcdate", DateTime, nullable=False),
    Column("dcflag", Integer, nullable=False),
    Column("taxflag", Integer, default=22),
    Column("contents", JSONB),
    Column("tax", JSONB),
    Column("cess", JSONB),
    Column("issuername", UnicodeText),
    Column("designation", UnicodeText),
    Column("noofpackages", Integer, nullable=False),
    Column("modeoftransport", UnicodeText),
    Column("attachment", JSON, CheckConstraint("length(attachment::text) <= %d" % (MAX_UPLOAD_SIZE), name="check_attachment_size")),
    Column("consignee", JSONB),
    Column("taxstate", UnicodeText),
    Column("sourcestate", UnicodeText),
    Column("orgstategstin", UnicodeText),
    Column("freeqty", JSONB),
    Column("discount", JSONB),
    Column("discflag", Integer, default=1),
    Column("vehicleno", UnicodeText),
    Column("dateofsupply", DateTime),
    Column("delchaltotal", Numeric(13, 2), nullable=False),
    Column("attachmentcount", Integer, default=0),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("custid", Integer, ForeignKey("customerandsupplier.custid")),
    Column("orderid", Integer, ForeignKey("purchaseorder.orderid")),
    Column("inoutflag", Integer, nullable=False),
    Column("dcnarration", UnicodeText),
    Column("roundoffflag", Integer, default=0),
    Column("goid", Integer, ForeignKey("godown.goid")),
    Column("totalinword", UnicodeText),
    Index("delchalbin_orgcodeindex", "orgcode"),
    Index("delchalbin_dcnoindex", "dcno"),
    info={
        "key_related_json_fields": {
            "contents": "product",
            "tax": "product",
            "cess": "product",
            "freeqty": "product",
            "discount": "product"
        }
    },
)
"""
The join table which has keys from both inv and dc table.
As explained before, one invoice may have many dc and one dc can be partially passed for many invoices.
"""
dcinv = Table(
    "dcinv",
    metadata,
    Column("dcinvid", Integer, primary_key=True),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("dcid", Integer, ForeignKey("delchal.dcid", ondelete="CASCADE")),
    Column("invid", Integer, ForeignKey("invoice.invid", ondelete="CASCADE")),
    Column("invprods", JSONB),
    UniqueConstraint("orgcode", "dcid", "invid"),
    Index("deinv_orgcodeindex", "orgcode"),
    Index("deinv_dcidindex", "dcid"),
    Index("deinv_invidindex", "invid"),
    info={"key_related_json_fields": {"invprods": "product"}},
)
"""
Table for stock.
This table records movement of goods and can give details either on basis of productcode,
invoice or dc (which ever is responsible for the movement ),
or by godown using the goid.
It has a field for product quantity.
it also has a field called dcinvtnflag which can tell if this movement was due to delivery chalan (flag = 4) or invoice (flag = 9 ) or cash memo (flag = 3) or transfernote (flag = 20), rejection note(flag = 18), quantity adjustments using Debit/Credit Note(flag = 7) or rejection of goods of bad quality(flag = 2).

This flag is necessary because,
Some times no dc is issued and a direct invoice is made (eg. cash memo at POS ).
So movements will be directly on invoice.
This is always the case when we purchase goods.
The inout field for in = 9 is stored and out = 15.

rate field denotes the rate at which the product was sold or transacted at
"""
stock = Table(
    "stock",
    metadata,
    Column("stockid", Integer, primary_key=True),
    Column("productcode", Integer, ForeignKey("product.productcode"), nullable=False),
    Column("stockdate", DateTime),
    Column("qty", Numeric(13, 2), nullable=False),
    Column("rate", Numeric(13, 2), nullable=False, default=0.00),
    Column("dcinvtnid", Integer, nullable=False),
    Column("dcinvtnflag", Integer, nullable=False),
    Column("inout", Integer, nullable=False),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("goid", Integer, ForeignKey("godown.goid", ondelete="CASCADE")),
    Index("stock_orgcodeindex", "orgcode"),
    Index("stock_productcodeindex", "productcode"),
    Index("stock_dcinvtnid", "dcinvtnid"),
)


""" table to store users for an organization.
Table for storing users for a particular organisation.
So orgcode is foreign key like other tables.
In addition this table has a field userrole which determines if the user is an admin:-1 manager:0 or operater:1 internal auditor:2 Godown In Charge:3

userconf Format:
{
    page_id: {
        config_id: {
            config
        }
    }
}

page_id and config_id will be stored in client side as enums.

Note: Users has been migrated to gkusers table
"""
users = Table(
    "users",
    metadata,
    Column("userid", Integer, primary_key=True),
    Column("username", Text, nullable=False),
    Column("userpassword", Text, nullable=False),
    Column("userrole", Integer, nullable=False),
    Column("userquestion", Text, nullable=False),
    Column("useranswer", Text, nullable=False),
    Column("themename", Text, default="Default"),
    Column("userconf", JSONB, default="{}"),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("orgcode", "username"),
    Index("userindex", "orgcode", "username"),
)

"""
Table for storing users of GNUKhata. Each user can be part of many organisations in GNUKhata.

orgs -> stores the list of orgs a user is part of. Also contains some org related data like invitestatus, orgspecific userconf and user's role.

orgs Format:
{
    orgcode: {
        invitestatus
        userconf
        userrole
        golist // if invite status is false, if the user has godown permissions, they will be stored here before being transfered to usergodowns table
    }
}

"""

gkusers = Table(
    "gkusers",
    metadata,
    Column("userid", Integer, primary_key=True),
    Column("username", Text, nullable=False),
    Column("userpassword", Text, nullable=False),
    Column("userquestion", Text, nullable=False),
    Column("useranswer", Text, nullable=False),
    Column("orgs", JSONB, default="{}"),
    UniqueConstraint("username"),
    Index("gkuserindex", "username"),
    info={"key_related_json_fields": {"orgs": "organisation"}},
)

""" the table for storing bank reconciliation data.
Every row will have voucher code for which the transaction is being checked against bank record.
"""
bankrecon = Table(
    "bankrecon",
    metadata,
    Column("reconcode", Integer, primary_key=True),
    Column(
        "vouchercode",
        Integer,
        ForeignKey("vouchers.vouchercode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "accountcode",
        Integer,
        ForeignKey("accounts.accountcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("clearancedate", DateTime),
    Column("memo", Text),
    Column("entry_type", Text),
    Column("amount", Float),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Index("bankrecoindex", "clearancedate"),
)
"""
This is the table which acts as a bin for deleted vouchers.
While these vouchers can't be recovered, they are for investigation purpose if need be.
"""
voucherbin = Table(
    "voucherbin",
    metadata,
    Column("vouchercode", Integer, primary_key=True),
    Column("vouchernumber", UnicodeText, nullable=False),
    Column("voucherdate", DateTime, nullable=False),
    Column("narration", UnicodeText),
    Column("drs", JSONB, nullable=False),
    Column("crs", JSONB, nullable=False),
    Column("vouchertype", UnicodeText, nullable=False),
    Column("projectname", UnicodeText, nullable=True),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Index("binvoucher_orgcodeindex", "orgcode"),
    Index("binvoucher_vno", "vouchernumber"),
    Index("binvoucher_vdate", "voucherdate"),
)

"""
table for purchase order.
This may or may not link to a certain invoice.
However if it is linked then we will have to compare the items with those in invoice.
psflag will be either 16 or 20 for purchase order and sales order respectively.

Here schedule json field will be having all the product details in format,
product code is key and value will be dictionary having product name, quantity, price per unit, number of packages, reorder limit, tax rate,
and  dictionary for saving staggered delivery details whose key will be date and value will be quantity.
Roundoff field is to check wheather purchase/sales order total is rounded off or not. 
0 = no round off 1 = total amount rounded off.
"""
purchaseorder = Table(
    "purchaseorder",
    metadata,
    Column("orderid", Integer, primary_key=True),
    Column("orderno", UnicodeText, nullable=False),
    Column("orderdate", DateTime, nullable=False),
    Column("psnarration", UnicodeText),
    Column("creditperiod", UnicodeText),
    Column("payterms", UnicodeText),
    Column("modeoftransport", UnicodeText),
    Column("issuername", UnicodeText),
    Column("designation", UnicodeText),
    Column("schedule", JSONB),
    Column("taxstate", UnicodeText),
    Column("psflag", Integer, nullable=False),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "csid",
        Integer,
        ForeignKey("customerandsupplier.custid", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("togodown", Integer, ForeignKey("godown.goid", ondelete="CASCADE")),
    Column("taxflag", Integer, default=22),
    Column("tax", JSONB),
    Column("cess", JSONB),
    Column("purchaseordertotal", Numeric(13, 2), nullable=False),
    Column("pototalwords", UnicodeText),
    Column("sourcestate", UnicodeText),
    Column("orgstategstin", UnicodeText),
    Column("attachment", JSON, CheckConstraint("length(attachment::text) <= %d" % (MAX_UPLOAD_SIZE), name="check_attachment_size")),
    Column("attachmentcount", Integer, default=0),
    Column("consignee", JSONB),
    Column("freeqty", JSONB),
    Column("reversecharge", UnicodeText),
    Column("bankdetails", JSONB),
    Column("vehicleno", UnicodeText),
    Column("dateofsupply", DateTime),
    Column("discount", JSONB),
    Column("paymentmode", Integer, default=2),
    Column("address", Text),
    Column("pincode", UnicodeText),
    Column("roundoffflag", Integer, default=0),
    Column("immutable_data_id", Integer, ForeignKey("transaction.transaction_id")),
    Index("purchaseorder_orgcodeindex", "orgcode"),
    Index("purchaseorder_date", "orderdate"),
    Index("purchaseorder_togodown", "togodown"),
    info={
        "key_related_json_fields": {
            "schedule": "product",
            "tax": "product",
            "cess": "product",
            "freeqty": "product",
            "discount": "product"
        }
    },
)


"""
Table for storing godown details.
Basically one organization may have many godowns and we aught to know from which one goods have moved out.
"""
godown = Table(
    "godown",
    metadata,
    Column("goid", Integer, primary_key=True),
    Column("goname", UnicodeText),
    Column("goaddr", UnicodeText),
    Column("state", UnicodeText),
    Column("gocontact", UnicodeText),
    Column("contactname", UnicodeText),
    Column("designation", UnicodeText),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("orgcode", "goname"),
    Index("godown_orgcodeindex", "orgcode"),
)

"""
table for budget module. All types of budget will store in this table.
content field will have budget with its account/group/subgroup(key) and budget(value).
budtype is for budget type: cash(3)/expense(5)/sales(19).
gaflag is for budget is group wise(7)/subgroup wise(19)/account wise(1)
budget period: startdate to enddate.
project code field: cost center or project wise budget.
"""
budget = Table(
    "budget",
    metadata,
    Column("budid", Integer, primary_key=True),
    Column("budname", UnicodeText, nullable=False),
    Column("startdate", DateTime, nullable=False),
    Column("enddate", DateTime, nullable=False),
    Column("contents", JSONB, nullable=False),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("budtype", Integer, nullable=False),
    Column("projectcode", Integer, ForeignKey("projects.projectcode")),
    Column("gaflag", Integer, nullable=False),
    info={"key_related_json_fields": {"contents": "accounts"}},
)

"""
Table for storing product godownwise.
When products are stored in the different godowns its openingstick will be entered accordingly.
"""
goprod = Table(
    "goprod",
    metadata,
    Column("goprodid", Integer, primary_key=True),
    Column(
        "goid", Integer, ForeignKey("godown.goid", ondelete="CASCADE"), nullable=False
    ),
    Column(
        "productcode",
        Integer,
        ForeignKey("product.productcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("goopeningstock", Numeric(13, 2), default=0.00, nullable=False),
    Column("openingstockvalue", Numeric(13, 2), default=0.00, nullable=False),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("goid", "productcode", "orgcode"),
    Index("godown_product", "productcode"),
)
# now table for user godown rights.
usergodown = Table(
    "usergodown",
    metadata,
    Column("ugid", Integer, primary_key=True),
    Column("goid", Integer, ForeignKey("godown.goid", ondelete="CASCADE")),
    Column("userid", Integer, ForeignKey("gkusers.userid", ondelete="CASCADE")),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
)

""" Table for transferNote details.
    When the goods are to be trasnferred from one godown to another or from godown to factory floor, or vice versa.

"""

transfernote = Table(
    "transfernote",
    metadata,
    Column("transfernoteid", Integer, primary_key=True),
    Column("transfernoteno", UnicodeText),
    Column("transfernotedate", DateTime, nullable=False),
    Column("transportationmode", UnicodeText),
    Column("nopkt", Integer),
    Column("issuername", UnicodeText),
    Column("designation", UnicodeText),
    Column("recieved", BOOLEAN, default=False),
    Column("recieveddate", DateTime),
    Column("duedate", DateTime),
    Column("grace", Integer),
    Column(
        "fromgodown",
        Integer,
        ForeignKey("godown.goid", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "togodown",
        Integer,
        ForeignKey("godown.goid", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("immutable_data_id", Integer, ForeignKey("transaction.transaction_id")),
    UniqueConstraint("transfernoteno", "orgcode"),
    Index("transfernote_date", "transfernotedate"),
    Index("transfernote_togodown", "togodown"),
    Index("transfernote_orgcode", "orgcode"),
)


"""
table to store tax for products along with the time they are valid for
This taxex would be vat , gst etc. For particular product and category (mutually exelusive)
"""
tax = Table(
    "tax",
    metadata,
    Column("taxid", Integer, primary_key=True),
    Column("taxname", UnicodeText, nullable=False),
    Column("taxrate", Numeric(5, 2), nullable=False),
    Column("taxfromdate", Date, nullable=False),
    Column("state", UnicodeText),
    Column(
        "productcode",
        Integer,
        ForeignKey("product.productcode", ondelete="CASCADE"),
    ),
    Column(
        "categorycode",
        Integer,
        ForeignKey("categorysubcategories.categorycode", ondelete="CASCADE"),
    ),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint(
        "taxname", "state", "taxrate", "taxfromdate", "productcode", "orgcode"
    ),
    Index("taxindex", "productcode", "taxname"),
    Index("tax_taxindex", "categorycode", "taxname"),
)

"""Table to store Log of users
This table will store all the activities made by different users. eg. created account at this time, deleted account, created voucher, etc."""
log = Table(
    "log",
    metadata,
    Column("logid", Integer, primary_key=True),
    Column("time", DateTime),
    Column("activity", UnicodeText),
    Column("userid", Integer, ForeignKey("gkusers.userid")),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Index("logindex", "userid", "activity"),
)

"""Table to store Rejection Note
This table will store invoice or delivery note id against which rejection note prepared
inout is a flag to indicate rejection in or out. in = 9, out = 15
rejprods is to store productcode as key and rejected quantity as value
"""
rejectionnote = Table(
    "rejectionnote",
    metadata,
    Column("rnid", Integer, primary_key=True),
    Column("rnno", UnicodeText, nullable=False),
    Column("rndate", DateTime, nullable=False),
    Column("inout", Integer, nullable=False),
    Column("rejprods", JSONB, nullable=False),
    Column("dcid", Integer, ForeignKey("delchal.dcid", ondelete="CASCADE")),
    Column("invid", Integer, ForeignKey("invoice.invid", ondelete="CASCADE")),
    Column("issuerid", Integer, ForeignKey("gkusers.userid")),
    Column("rejectedtotal", Numeric(13, 2), nullable=False),
    Column("rejnarration", UnicodeText),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("rnno", "inout", "orgcode"),
    Index("rejection_note", "orgcode"),
    info={"key_related_json_fields": {"rejprods": "product"}},
)

"""
This table is for stroring records of debit note and credit note.
The dctypeflag is used to decide whether it is debit note or credit note.(debit note=4 & credit note=3).
Debit/Credit Note number is stored in drcrno and drcrdate fields respectively.
These may be issued when there is differnce is taxable amount or when quantity is rejected.
If they are issued against an invoice its id is stored in invid.
If they are issued against a rejection note its id is stored in rnid.
Debited/Credited value of each product is stored in reductionval as values in a dictionary where keys are productcodes.
Debit/Credit Note reference if any is stored in reference field.
Documents attached is stored in attachment and its count stored in attachmentcount.
Storing userid helps access username and userrole.
check enum.py for all possible values of "drcrmode"
drcrmode = 4 (discounts), 18 (returns)
"""
drcr = Table(
    "drcr",
    metadata,
    Column("drcrid", Integer, primary_key=True),
    Column("drcrno", UnicodeText, nullable=False),
    Column("invid", Integer, ForeignKey("invoice.invid")),
    Column("drcrnarration", UnicodeText),
    Column("rnid", Integer, ForeignKey("rejectionnote.rnid")),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("drcrdate", DateTime, nullable=False),
    Column("drcrmode", Integer, default=4),
    Column("dctypeflag", Integer, default=3),
    Column("totreduct", Numeric(13, 2), default=0.00),
    Column("reductionval", JSONB),
    Column("reference", JSONB),
    Column("attachment", JSON, CheckConstraint("length(attachment::text) <= %d" % (MAX_UPLOAD_SIZE), name="check_attachment_size")),
    Column("attachmentcount", Integer, default=0),
    Column("userid", Integer, ForeignKey("gkusers.userid")),
    Column("roundoffflag", Integer, default=0),
    UniqueConstraint("orgcode", "drcrno", "dctypeflag"),
    UniqueConstraint("orgcode", "invid", "dctypeflag"),
    UniqueConstraint("orgcode", "rnid", "dctypeflag"),
    info={"key_related_json_fields": {"reductionval": "product"}},
)
"""
Bank Table
===========

This table records bank accounts of the organisation.

Fields:
account_name: Name of the account
bank_name: Bank name
branch_name: Branch name
ifsc_code: IFSC code
account_number: Account number
orgcode: Organisation code
accountcode: Account code
"""

bank = Table(
    "bank",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("account_name", UnicodeText, nullable=False),
    Column("bank_name", UnicodeText),
    Column("branch_name", UnicodeText),
    Column("ifsc", UnicodeText),
    Column("account_number", UnicodeText),
    Column(
        "orgcode",
        Integer,
        ForeignKey("organisation.orgcode", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "accountcode",
        Integer,
        ForeignKey("accounts.accountcode", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("orgcode", "account_name"),
    UniqueConstraint("accountcode", "account_name"),
)
