REGIONS = [
    {
        "id": "western_cape",
        "name": "Western Cape",
        "areas": [
            {
                "id": "false_bay",
                "name": "False Bay",
                "lat": -34.16,
                "lon": 18.47,
                "coast_facing": "SE",
                "notes": "Sheltered from NW wind, watch southerly swell.",
                "legal": "Some MPAs near Simon's Town – check access zones.",
            },
            {
                "id": "overberg",
                "name": "Overberg",
                "lat": -34.48,
                "lon": 20.06,
                "coast_facing": "S",
                "notes": "Open coast, more swell exposure.",
                "legal": "Check De Hoop/Agulhas MPA limits.",
            },
            {
                "id": "west_coast",
                "name": "West Coast",
                "lat": -33.02,
                "lon": 17.94,
                "coast_facing": "W",
                "notes": "Colder upwelling, stronger SW swell.",
                "legal": "Langebaan lagoon MPAs apply.",
            },
            {
                "id": "cape_town_atlantic",
                "name": "Atlantic Seaboard",
                "lat": -33.95,
                "lon": 18.38,
                "coast_facing": "W",
                "notes": "Cold upwelling, fast weather shifts, kelp beds.",
                "legal": "Robben Island/Two Oceans MPAs nearby; check beach permits.",
            },
            {
                "id": "garden_route",
                "name": "Garden Route",
                "lat": -34.05,
                "lon": 23.37,
                "coast_facing": "SSE",
                "notes": "Variable swell with reefy points and beaches.",
                "legal": "Tsitsikamma MPA strict no-take; Mossel Bay zones apply.",
            },
        ],
    },
    {
        "id": "eastern_cape",
        "name": "Eastern Cape",
        "areas": [
            {
                "id": "east_london",
                "name": "East London",
                "lat": -33.03,
                "lon": 27.91,
                "coast_facing": "E",
                "notes": "Warm Agulhas current influence, beach drops off quickly.",
                "legal": "Urban MPAs apply around Nahoon/Bonza Bay.",
            },
            {
                "id": "port_elizabeth",
                "name": "Gqeberha / Port Elizabeth",
                "lat": -33.97,
                "lon": 25.60,
                "coast_facing": "SE",
                "notes": "Algoa Bay shelter, watch NE wind for baitfish push.",
                "legal": "Algoa Bay MPA with island buffers.",
            },
            {
                "id": "wild_coast",
                "name": "Wild Coast",
                "lat": -31.62,
                "lon": 29.53,
                "coast_facing": "SE",
                "notes": "Rocky ledges, powerful surf, remote access.",
                "legal": "Multiple MPAs and community rules – confirm locally.",
            },
            {
                "id": "jeffreys_bay",
                "name": "Jeffreys Bay",
                "lat": -34.05,
                "lon": 24.92,
                "coast_facing": "ESE",
                "notes": "Point surf, current can rip on big swell.",
                "legal": "Municipal fishing bylaws; check seasonal restrictions.",
            },
            {
                "id": "port_alfred",
                "name": "Port Alfred",
                "lat": -33.59,
                "lon": 26.89,
                "coast_facing": "E",
                "notes": "River mouth dynamics change with rainfall.",
                "legal": "Check Kowie estuary rules and size/bag limits.",
            },
        ],
    },
    {
        "id": "kwazulu_natal",
        "name": "KwaZulu-Natal",
        "areas": [
            {
                "id": "durban",
                "name": "Durban",
                "lat": -29.86,
                "lon": 31.03,
                "coast_facing": "E",
                "notes": "Warmer water, sandbars shift after storms.",
                "legal": "Urban beaches with shark nets and pier zones.",
            },
            {
                "id": "south_coast",
                "name": "South Coast",
                "lat": -30.80,
                "lon": 30.43,
                "coast_facing": "E",
                "notes": "Reefs close inshore, good winter sardine run timing.",
                "legal": "Check seasonal sardine run restrictions.",
            },
            {
                "id": "north_coast",
                "name": "North Coast",
                "lat": -28.77,
                "lon": 32.06,
                "coast_facing": "ENE",
                "notes": "Warmer and clearer, pelagic shots when current is blue.",
                "legal": "iSimangaliso and other MPAs strictly enforced.",
            },
            {
                "id": "richards_bay",
                "name": "Richards Bay",
                "lat": -28.80,
                "lon": 32.10,
                "coast_facing": "ENE",
                "notes": "Harbour influence; check water clarity after rain.",
                "legal": "Harbour permits required; MPA buffers nearby.",
            },
        ],
    },
]

SPECIES_LEGAL_NOTES = {
    "galjoen": "Seasonal closures in parts of SA; confirm provincial dates before targeting.",
    "kob": "Bag/size limits vary; estuary mouth closures sometimes enforced.",
    "garrick": "Often catch-and-release encouraged; check current size limits.",
    "shad": "Closed season mid-October to end-November in many provinces; verify.",
    "yellowtail": "Offshore species; check bag limits when boating.",
    "steenbras": "Size/bag limits strict; be mindful of seasonal protections.",
    "snoek": "Commercial pressure high; respect quotas and size limits.",
    "roman": "Reef-associated; MPAs often prohibit take.",
    "hottentot": "Common reef fish; size limits apply.",
    "musselcracker": "Seasonal closures; strict size/bag limits in many provinces.",
    "blacktail": "Common surf species; observe size limits.",
    "bonito": "Pelagic; bag limits apply offshore.",
    "leerfish": "Often catch-and-release encouraged; check size limits.",
}


def list_regions():
    """Return region/area metadata for the UI."""
    return REGIONS


def find_region(region_id):
    return next((r for r in REGIONS if r["id"] == region_id), None)


def find_area(region_id, area_id):
    region = find_region(region_id)
    if not region:
        return None, None
    area = next((a for a in region.get("areas", []) if a["id"] == area_id), None)
    return region, area
