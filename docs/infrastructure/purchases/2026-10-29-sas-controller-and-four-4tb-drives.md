# Riverview infrastructure acquisitions — 2026-10-29 (SAS controller, four 4 TB disks, and breakout cable)

Status: PURCHASED / AWAITING DELIVERY
Source: purchaser-supplied eBay order-confirmation screenshots and pasted order details, 2026-10-29.
All purchase times below are as displayed by eBay; timezone not verified.

## Acquisition 1 — SAS HBA controller
- Item: HP LSI 9217-4i4e SAS 6 Gb/s RAID/HBA controller card, new sealed; HP part numbers 792099-001 and 725504-002
- Quantity: 1
- eBay item number: 186981019463
- Order number: 04-15372-09114
- Order placed: October 29, 2026, 10:49 AM (displayed time)
- Seller account: broad_sound_sales
- Unit/subtotal: USD 20.00
- Shipping: free
- Sales tax: USD 1.50
- Total charged: USD 21.50
- Payment method: Discover credit card ending 0283 (only last four recorded)
- Shipping: USPS Ground Advantage
- Expected arrival: November 2–5, 2026
- Tracking: not available at time of confirmation
- Returns: not accepted, per order page
- Intended role: 4 internal SAS lanes and 4 external SAS lanes for future SAS expander/JBOD shelf
- Installation host: OctoMiner1 or OctoMiner2, not yet decided
- Firmware mode: unknown until hardware inspection; IT-mode conversion may be needed
- Source: purchaser-supplied order details

## Acquisition 2 — Four 4 TB SAS disks
- Item: EMC Seagate Constellation 4 TB ST4000NM0023, erased and tested, Glist0, 520-byte block size
- Quantity: 4
- Raw capacity: 16 TB decimal total
- eBay item number: 198752648342
- Order number: 27-15327-87556
- Order placed: October 29, 2026, 6:39 AM (displayed time)
- Seller account: lennyg996
- Merchandise subtotal (four drives): USD 72.00
- Shipping: USD 6.63
- Sales tax: USD 5.90
- Total charged: USD 84.53
- Payment method: Discover credit card ending 0283 (only last four recorded)
- Tracking number: 384391860262 (carrier not confirmed in supplied record)
- Expected arrival: Tuesday, November 3, 2026
- Returns: accepted through December 3, 2026
- Condition: used, per order page
- Required commissioning: inspect each drive and convert 520-byte sectors to 512-byte sectors as appropriate; destructive formatting only after identity verification
- Source: purchaser-supplied order details

## Acquisition 3 — Internal SAS breakout cable
- Item: Mini SAS SFF-8087 to 4 × SFF-8482 breakout cable, 1 meter, with SATA power connectors for SAS drives
- Quantity: 1
- eBay item number: 137535422343
- Order number: 10-15360-62837
- Order placed: October 29, 2026, 11:29 AM (displayed time; timezone unverified)
- Seller account: ssus-tstore
- Condition: new
- Merchandise subtotal: USD 13.94
- Shipping: free
- Sales tax: USD 1.05
- Total charged: USD 14.99
- Payment method: Discover credit card ending 0283 (only last four recorded)
- Carrier: USPS
- Shipping service: USPS First Class
- Expected arrival: October 31 – November 3, 2026
- Tracking: not yet available at confirmation
- Intended role: internal SFF-8087 port on HP LSI 9217-4i4e to four 3.5-inch SAS SFF-8482 drive connectors; drive power source/capacity to be confirmed before installation
- Source: purchaser-supplied eBay order confirmation and order-detail screenshots, October 29, 2026

## Acquisition totals
- Controller: USD 21.50
- Drives: USD 84.53
- Internal SAS breakout cable: USD 14.99
- Total confirmed purchases: **USD 121.02**
- Additional power adapters/splitters discussed but **not confirmed purchased** in supplied evidence; exclude from acquisition total.

## Purchasing account attribution
- Platform: eBay
- Signed-in greeting visible: **Hi patricia!**
- Actual eBay username/account ID: **not verified from supplied evidence**
- Purchaser name and shipping address appear in source order confirmations; omitted from this repository record to minimize unnecessary personal information.
- Payment account recorded only as card brand and last four digits, with purchaser's authorization.

## Follow-up upon delivery
- Capture delivery date and controller tracking.
- Confirm controller's PCI IDs, firmware mode and link width; confirm cabling.
- Record each disk's serial number, health and 512-byte conversion outcome.
- Update installation host and deployed inventory location.

## Relationship to earlier hardware acquisitions
- This entry covers only the three purchases documented above.
- Prior Tesla P100 acquisition records should be cross-linked once their existing canonical GitHub location is verified; no prior purchase record was changed or duplicated here.
