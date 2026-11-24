"""Read explicit operating segment and geographic contexts from an SEC XBRL instance."""

from datetime import date
from decimal import Decimal, InvalidOperation
from io import StringIO
import json
import re
from xml.etree import ElementTree as ET

XBRLI = "{http://www.xbrl.org/2003/instance}"
XBRLDI = "{http://xbrl.org/2006/xbrldi}"
US_GAAP = ("{http://fasb.org/us-gaap/", "{https://fasb.org/us-gaap/")
SEGMENT_TAXONOMIES = (*US_GAAP, "{http://fasb.org/srt/", "{https://fasb.org/srt/")
SEGMENT_AXIS = "StatementBusinessSegmentsAxis"
GEOGRAPHY_AXIS = "StatementGeographicalAxis"
REVENUE = {"RevenueFromContractWithCustomerExcludingAssessedTax",
           "RevenueFromContractWithCustomerIncludingAssessedTax", "Revenues", "SalesRevenueNet"}
PREDICATES = {
    "OperatingIncomeLoss": (SEGMENT_AXIS, "operating_income_segment", False),
    "Assets": (SEGMENT_AXIS, "assets_segment", True),
    "LongLivedAssets": (GEOGRAPHY_AXIS, "long_lived_assets_geography", True),
}


def _qualified(value, namespaces):
    prefix, _, name = value.partition(":")
    if not name or prefix not in namespaces:
        raise ValueError("Unknown XBRL dimension name")
    return f"{{{namespaces[prefix]}}}{name}"


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _context(row, namespaces, cik):
    entity = row.find(XBRLI + "entity")
    period = row.find(XBRLI + "period")
    if entity is None or period is None:
        return None
    identity = entity.find(XBRLI + "identifier")
    if (identity is None or identity.get("scheme") != "http://www.sec.gov/CIK"
            or (identity.text or "").strip().lstrip("0") != cik.lstrip("0")):
        return None
    dimensions = {}
    try:
        for parent in (*entity.findall(XBRLI + "segment"), *row.findall(XBRLI + "scenario")):
            for member in parent:
                if member.tag != XBRLDI + "explicitMember":
                    return None
                axis = _qualified(member.attrib["dimension"], namespaces)
                if axis in dimensions:
                    return None
                dimensions[axis] = _qualified((member.text or "").strip(), namespaces)
        instant = period.findtext(XBRLI + "instant")
        end = date.fromisoformat(instant or period.findtext(XBRLI + "endDate", "")).isoformat()
        start = None if instant else date.fromisoformat(period.findtext(XBRLI + "startDate", "")).isoformat()
    except (ValueError, KeyError):
        return None
    if not dimensions or (start and start > end):
        return None
    return dimensions, start, end


def dimensions_from_instance(xml, cik, accession):
    """Return standard US GAAP monetary facts and complete explicit axis-member combinations."""
    if len(xml) > 64_000_000 or "<!DOCTYPE" in xml.upper():
        raise ValueError("Unsupported SEC XBRL instance")
    namespaces = {}
    try:
        parsed = ET.iterparse(StringIO(xml), events=("start-ns", "end"))
        for event, value in parsed:
            if event == "start-ns":
                prefix, uri = value
                if prefix in namespaces and namespaces[prefix] != uri:
                    raise ValueError("Conflicting namespace declarations in SEC XBRL instance")
                namespaces[prefix] = uri
    except ET.ParseError:
        raise ValueError("Invalid SEC XBRL instance") from None
    root = parsed.root
    if root.tag != XBRLI + "xbrl":
        raise ValueError("Expected an SEC XBRL instance document")
    contexts = {row.get("id"): _context(row, namespaces, cik) for row in root.findall(XBRLI + "context")}
    units = {}
    for row in root.findall(XBRLI + "unit"):
        if len(row) != 1 or row[0].tag != XBRLI + "measure":
            continue
        prefix, _, currency = (row[0].text or "").strip().partition(":")
        if namespaces.get(prefix) == "http://www.xbrl.org/2003/iso4217" and re.fullmatch(r"[A-Z]{3}", currency):
            units[row.get("id")] = currency
    facts = []
    for row in root:
        if not row.tag.startswith(US_GAAP):
            continue
        concept = _local(row.tag)
        context = contexts.get(row.get("contextRef"))
        unit = units.get(row.get("unitRef"))
        if not context or not unit or (concept not in REVENUE and concept not in PREDICATES):
            continue
        dim, start, end = context
        axes = {_local(axis) for axis in dim if axis.startswith(SEGMENT_TAXONOMIES)}
        predicates = []
        if concept in REVENUE and start:
            predicates = [predicate for axis, predicate in (
                (SEGMENT_AXIS, "revenue_segment"), (GEOGRAPHY_AXIS, "revenue_geography")) if axis in axes]
        elif concept in PREDICATES:
            axis, predicate, instant = PREDICATES[concept]
            if axis in axes and instant == (start is None):
                predicates = [predicate]
        if not predicates or row.text is None:
            continue
        try:
            value = Decimal(row.text.strip())
        except InvalidOperation:
            continue
        if not value.is_finite():
            continue
        key = json.dumps(sorted(dim.items()), separators=(",", ":"))
        label = "; ".join(f"{_local(axis)}={_local(member)}" for axis, member in sorted(dim.items()))
        facts.extend({"accession": accession, "predicate": predicate, "key": key, "label": label,
                      "taxonomy": "us-gaap", "concept": concept, "unit": unit,
                      "period_start": start, "period_end": end, "value": str(value)}
                     for predicate in predicates)
    return facts
