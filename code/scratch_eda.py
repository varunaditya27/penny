import csv

with open("dataset/sample_requests.csv") as f:
    samples = list(csv.DictReader(f))

with open("dataset/financial_profiles.csv") as f:
    profiles = {p["user_id"]: p for p in csv.DictReader(f)}

with open("dataset/financial_events.csv") as f:
    events = list(csv.DictReader(f))

with open("dataset/messages.csv") as f:
    messages = list(csv.DictReader(f))

with open("dataset/images.csv") as f:
    images = list(csv.DictReader(f))

with open("dataset/financial_events.csv") as f:
    events = {e["event_id"]: e for e in csv.DictReader(f)}

print(f"Total images: {len(images)}")
for img in images:
    ev = events.get(img["related_event_id"], {})
    desc = ev.get("description", "")
    cat = ev.get("category", "")
    dt = ev.get("event_date", "")
    st = ev.get("status", "")
    print(img["image_id"] + " (" + img["user_id"] + ", " + img["related_event_id"] + "): " + desc + " | cat=" + cat + " | " + dt + " | " + st)

