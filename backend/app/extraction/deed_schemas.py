from typing import Dict, List, Any

class FieldSpec:
    def __init__(self, name: str, description: str, example: str):
        self.name = name
        self.description = description
        self.example = example

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "example": self.example
        }

SALE_DEED_FIELDS = [
    FieldSpec(
        "document_date",
        "The date on which the sale deed was executed, usually in DD-MM-YYYY format.",
        "15-06-2025"
    ),
    FieldSpec(
        "seller_name",
        "The name of the vendor or seller transferring the property.",
        "Ramesh Kumar"
    ),
    FieldSpec(
        "buyer_name",
        "The name of the purchaser or buyer acquiring the property.",
        "Suresh Kumar"
    ),
    FieldSpec(
        "sale_consideration",
        "The monetary amount paid for the transaction, including currency.",
        "Rs. 8,50,000"
    ),
    FieldSpec(
        "survey_number",
        "The official survey number or plot number of the land record.",
        "124/3"
    ),
    FieldSpec(
        "area",
        "The size or area of the property, including units (e.g. acres, hectares).",
        "2.45 Acres"
    ),
    FieldSpec(
        "property_location",
        "The physical address or bounding description of the land plot.",
        "Plot 14, Sector 5, Rampur"
    ),
    FieldSpec(
        "village",
        "The village or locality where the property is located.",
        "Rampur"
    ),
    FieldSpec(
        "district",
        "The name of the district.",
        "Kurukshetra"
    ),
    FieldSpec(
        "registration_details",
        "Official registry numbers (e.g., book number, volume number, document number).",
        "Reg No: 543/2025"
    ),
    FieldSpec(
        "seller_address",
        "The address of the seller/vendor as stated in the deed.",
        "House No 12, Rampur"
    ),
    FieldSpec(
        "buyer_address",
        "The address of the buyer/purchaser as stated in the deed.",
        "House No 45, Kurukshetra"
    )
]

# Kept separate so the established English Sale Deed response remains stable.
# The extractor uses these fields only for the explicit Kannada Sale Deed type.
KANNADA_SALE_DEED_FIELDS = [
    FieldSpec("document_date", "The date on which the sale deed was executed, usually in DD-MM-YYYY format.", "15-06-2025"),
    FieldSpec("seller_name", "The name of the vendor or seller transferring the property.", "ಮಾರಾಟಗಾರ"),
    FieldSpec("seller_address", "The address of the seller/vendor as stated in the deed.", "ಮಾರಾಟಗಾರರ ವಿಳಾಸ"),
    FieldSpec("buyer_name", "The name of the purchaser or buyer acquiring the property.", "ಖರೀದಿದಾರ"),
    FieldSpec("buyer_address", "The address of the buyer/purchaser as stated in the deed.", "ಖರೀದಿದಾರರ ವಿಳಾಸ"),
    FieldSpec("khata_number", "Khata number of the land property.", "456"),
    FieldSpec("survey_number", "The official survey number or plot number of the land record.", "124/3"),
    FieldSpec("area", "The size or area of the property, including units.", "2.45 Acres"),
    FieldSpec("road", "Road or street name where property is located.", "Main Road"),
    FieldSpec("village", "The village or locality where the property is located.", "Bengaluru"),
    FieldSpec("taluk", "Taluk name.", "Bengaluru South"),
    FieldSpec("district", "The name of the district.", "Bengaluru Urban"),
    FieldSpec("city", "City name.", "Bengaluru"),
    FieldSpec("state", "State name.", "Karnataka"),
]

PARTITION_DEED_FIELDS = [
    FieldSpec(
        "document_date",
        "The date on which the partition deed was executed.",
        "01-03-2025"
    ),
    FieldSpec(
        "parties",
        "A comma-separated list of all co-owners or parties participating in the partition.",
        "Ramesh Kumar, Suresh Kumar, Priya Kumar"
    ),
    FieldSpec(
        "party_count",
        "The total number of parties partitioning the property (as an integer string).",
        "3"
    ),
    FieldSpec(
        "survey_number",
        "The survey number of the main land record partitioned.",
        "87"
    ),
    FieldSpec(
        "total_area",
        "The total combined area of the land record being partitioned.",
        "3.10 Acres"
    ),
    FieldSpec(
        "share_allocation",
        "How the total area is divided among the parties (e.g. Ramesh: 1.05 ac, Suresh: 1.05 ac, Priya: 1.00 ac).",
        "Ramesh: 1.05 acres, Suresh: 1.05 acres, Priya: 1.00 acres"
    ),
    FieldSpec(
        "village",
        "The name of the village where the partitioned land resides.",
        "Kalyanpur"
    ),
    FieldSpec(
        "district",
        "The name of the district.",
        "Kurukshetra"
    ),
    FieldSpec(
        "property_description",
        "Brief details or description of the partitions/boundaries of the property shares.",
        "Divided into three equal portions bounded by north, south, and main road."
    ),
    FieldSpec(
        "registration_details",
        "The official registration volume or number for the partition deed.",
        "Partition Deed Reg No: 876/2025"
    )
]

DOCUMENT_TYPE_SCHEMAS = {
    "Sale Deed": [f.to_dict() for f in SALE_DEED_FIELDS],
    "Kannada Sale Deed": [f.to_dict() for f in KANNADA_SALE_DEED_FIELDS],
    "Partition Deed": [f.to_dict() for f in PARTITION_DEED_FIELDS]
}
