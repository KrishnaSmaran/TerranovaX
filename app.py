from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# ── 🔧 YOUR GMAIL CONFIG ──
GMAIL_ADDRESS = "veeraragavansathyanarayanan@gmail.com"
GMAIL_PASSWORD = "ecyltpiffefyptkr"
# ─────────────────────────

# Store OTPs temporarily
otp_store = {}

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(to_email, otp):
    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = "TerranovaX - Your OTP Code"

    body = f"""
    <html>
    <body style="background:#050807; color:#d2d8d2; font-family:Inter,sans-serif; padding:30px;">
        <h2 style="color:#1f6f43;">TerranovaX Verification</h2>
        <p>Your OTP code is:</p>
        <h1 style="color:#7a1f2b; font-size:42px; letter-spacing:8px;">{otp}</h1>
        <p style="color:#888;">This code expires in 5 minutes.</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())

@app.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.json
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email required"}), 400
    otp = generate_otp()
    otp_store[email] = otp
    print(f"✅ OTP for {email}: {otp}")
    try:
        send_otp_email(email, otp)
        return jsonify({"message": "OTP sent!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.json
    email = data.get("email")
    otp = data.get("otp")
    print(f"🔍 Entered: {otp}, Stored: {otp_store.get(email)}")
    if otp_store.get(email) == otp:
        del otp_store[email]
        return jsonify({"message": "OTP verified!"}), 200
    return jsonify({"error": "Invalid OTP"}), 400


# ── FILE PATHS (store data next to app.py) ──
SUBSCRIBERS_FILE = "subscribers.json"
REACTIONS_FILE   = "reactions.json"

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            try: return json.load(f)
            except: return default
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── ROUTE: Subscribe ──
@app.route("/subscribe", methods=["POST"])
def subscribe():
    data  = request.json or {}
    email = data.get("email", "").strip().lower()

    if not email or "@" not in email:
        return jsonify({"error": "Valid email required"}), 400

    subscribers = load_json(SUBSCRIBERS_FILE, [])

    # Check duplicate
    if any(s["email"] == email for s in subscribers):
        return jsonify({"message": "Already subscribed"}), 409

    subscribers.append({
        "email": email,
        "joined": datetime.now().isoformat()
    })
    save_json(SUBSCRIBERS_FILE, subscribers)

    # Send welcome email
    try:
        send_welcome_email(email)
    except Exception as e:
        print(f"Welcome email failed: {e}")

    return jsonify({"message": "Subscribed!"}), 200


# ── ROUTE: Subscriber Count ──
@app.route("/api/subscriber-count", methods=["GET"])
def subscriber_count():
    subscribers = load_json(SUBSCRIBERS_FILE, [])
    return jsonify({"count": len(subscribers)})


# ── ROUTE: Channel Posts (location-aware) ──
@app.route("/api/channel-posts", methods=["GET"])
def channel_posts():
    lat  = request.args.get("lat",  type=float)
    lon  = request.args.get("lon",  type=float)
    city = request.args.get("city", "Your Area")

    reactions = load_json(REACTIONS_FILE, {})
    posts     = generate_location_posts(lat, lon, city, reactions)
    return jsonify(posts)

# ─────────────────────────────────────────────────────────────────
# POST POOL — each region has 10+ varied posts. 5 are picked at
# random each call so users see different content on refresh.
# Types: green = awareness/good news, brown = advisory, red = alert
# These are climate AWARENESS posts, not official emergency alerts.
# ─────────────────────────────────────────────────────────────────

def generate_location_posts(lat, lon, city, reactions):
    region = detect_region(lat, lon)
    pool   = get_post_pool(region, city)
    random.shuffle(pool)
    selected = pick_diverse(pool, count=5)
    now  = datetime.now()
    offsets = [8, 22, 65, 140, 210]
    result = []
    for i, p in enumerate(selected):
        pid = p["id"]
        r   = reactions.get(pid, {})
        result.append({
            "id":       pid,
            "type":     p["type"],
            "location": p.get("location", city),
            "time":     (now - timedelta(minutes=offsets[i])).isoformat(),
            "thumbsUp": r.get("thumbsUp", random.randint(0, 18)),
            "fire":     r.get("fire",     random.randint(0, 10)),
            "sad":      r.get("sad",      random.randint(0, 8)),
            "text":     p["text"],
        })
    return result


def pick_diverse(pool, count=5):
    greens = [p for p in pool if p["type"] == "green"]
    browns = [p for p in pool if p["type"] == "brown"]
    reds   = [p for p in pool if p["type"] == "red"]
    chosen = []
    if greens: chosen.append(greens.pop(0))
    if browns: chosen.append(browns.pop(0))
    if reds:   chosen.append(reds.pop(0))
    rest = greens + browns + reds
    random.shuffle(rest)
    chosen += rest[:count - len(chosen)]
    random.shuffle(chosen)
    return chosen[:count]


def get_post_pool(region, city):
    """Return a pool of 10-12 varied posts for the given region."""

    if region == "india_south":
        return [
            {
                "id": "is_01", "type": "green",
                "location": f"{city}, South India",
                "text": f"✅ <b>Air Quality Report — {city}: Good</b>\n\nCurrent AQI in {city} is 48 — firmly in the 'Good' category. PM2.5 levels at 16 µg/m³ are well within WHO safe limits.\n\n🌬️ Sea breeze off the Bay of Bengal is keeping pollutant levels low across coastal Tamil Nadu and Andhra Pradesh today. UV Index is High (7/10) — apply SPF 30+ if you're outdoors for extended periods.\n\n🌡️ Today's forecast: 31°C max · 24°C min · 70% humidity · Partly cloudy\n\n📊 <i>Source: TerranovaX regional sensor network · Updated hourly</i>"
            },
            {
                "id": "is_02", "type": "green",
                "location": "Tamil Nadu / Karnataka",
                "text": "✅ <b>Southwest Monsoon — Healthy Progress</b>\n\nThe Southwest Monsoon is performing well above expectations this season. Cumulative rainfall for Tamil Nadu stands at 112% of the Long Period Average (LPA), while Karnataka has recorded 108% LPA.\n\n🌾 This is excellent news for the Kharif crop season. Paddy transplantation is on schedule across the Cauvery delta region. Water levels in the Mettur, KRS, and Krishnagiri reservoirs are at 78% capacity — well above last year's 54% at this point.\n\n🌱 Groundwater recharge in Chennai's aquifer zones has improved by 14% compared to the 10-year average.\n\n📡 <i>TerranovaX satellite rainfall analysis · Data cross-checked with IMD</i>"
            },
            {
                "id": "is_03", "type": "green",
                "location": f"{city}",
                "text": f"✅ <b>Cyclone Season Outlook — Lower Risk This Year</b>\n\nIMD's seasonal forecast for the Bay of Bengal indicates a below-normal cyclone season for 2025, with an estimated 2–3 cyclonic disturbances likely, compared to the long-term average of 4.5.\n\n🌊 Sea surface temperatures in the Bay remain within normal range, reducing rapid intensification risk. Wind shear conditions are moderately unfavourable for cyclone development through mid-October.\n\n☀️ This does not mean zero risk — always stay alert during October–December. TerranovaX will notify you immediately if a system threatens your area.\n\n📊 <i>Source: IMD Extended Range Forecast · TerranovaX Bay of Bengal Monitor</i>"
            },
            {
                "id": "is_04", "type": "brown",
                "location": "Bay of Bengal",
                "text": "⚠️ <b>Bay of Bengal — Monitoring Low-Pressure Area</b>\n\nTerranovaX satellites are tracking a low-pressure area that has formed over the west-central Bay of Bengal. At this stage it is a weak system and has NOT intensified beyond a depression.\n\n🌀 Current wind speeds near the center: 35–40 km/h · Sea state: moderate to rough\n\n📍 Most models suggest the system will weaken over the next 48 hours due to increased vertical wind shear. However, TerranovaX is monitoring at 3-hour intervals and will issue an immediate alert if the system strengthens.\n\n⛵ Fishermen: Exercise caution in waters beyond 40km from the coast.\n\n📡 <i>Next update in 3 hours · TerranovaX Ocean Monitoring System</i>"
            },
            {
                "id": "is_05", "type": "brown",
                "location": f"{city} Region",
                "text": f"⚠️ <b>Seasonal Heat Advisory — Afternoons</b>\n\nTemperatures in {city} are expected to peak at 37–39°C this week due to reduced cloud cover. While this is within the normal summer range for the region, the combination of high humidity (72%) means the 'feels like' temperature could reach 44°C during peak afternoon hours (1 PM – 4 PM).\n\n💧 Stay hydrated — drink water regularly even if not thirsty. Avoid direct sun exposure during peak afternoon hours. Light-coloured, loose clothing recommended.\n\n👴 Check on elderly relatives and neighbours. Young children should not play outdoors between 12 PM – 4 PM.\n\n🌡️ <i>This is a seasonal advisory, not an emergency alert. Conditions are typical for this time of year.</i>"
            },
            {
                "id": "is_06", "type": "brown",
                "location": "Coastal Tamil Nadu / Andhra Pradesh",
                "text": "⚠️ <b>High Tide Advisory — Coastal Areas</b>\n\nThe India Meteorological Department has issued a high tide advisory for coastal Tamil Nadu and southern Andhra Pradesh. Spring tides coinciding with onshore winds may cause temporary inundation of low-lying coastal areas near estuaries and river mouths.\n\n🌊 Expected tidal heights: 1.2–1.5m above Mean Sea Level at Chennai, Mahabalipuram, Pondicherry coastal stretch.\n\n🏖️ Advisory: Avoid walking on beaches and fishing piers during peak tide windows (6–8 AM and 6–8 PM today). Fishermen should secure boats above the high tide mark.\n\n📍 <i>This is a precautionary tide advisory, NOT a tsunami or storm surge warning.</i>"
            },
            {
                "id": "is_07", "type": "red",
                "location": "Bay of Bengal",
                "text": "🚨 <b>Cyclone Watch — Bay of Bengal System Intensifying</b>\n\nA depression over the Bay of Bengal has intensified into a Deep Depression with maximum sustained winds of 55–65 km/h. IMD expects further intensification into a cyclonic storm within the next 24 hours.\n\n🌀 Projected track: Moving northwest toward the Andhra Pradesh–Odisha coastline. Landfall probability: 58% within 72 hours.\n\n⚠️ Coastal residents from Vishakhapatnam to Kakinada district: Begin preparation now.\n• Secure all loose objects\n• Stock 3 days of food and water\n• Keep documents, medications, and power banks ready\n• Know your nearest evacuation shelter\n\n🚢 All fishing activity suspended.\n\n📞 NDRF: 0120-2309452 · Andhra SDMA: 1800-425-0101"
            },
            {
                "id": "is_08", "type": "red",
                "location": "South India",
                "text": "🚨 <b>Seismic Event — Andaman & Nicobar Region</b>\n\nThe National Centre for Seismology recorded a magnitude 5.4 earthquake at 02:47 IST near the Andaman Islands (12.8°N, 93.1°E), at a depth of 42km. This is the fourth tremor above M4.5 in this zone over the past 10 days.\n\n🌊 No tsunami warning has been issued — the earthquake's location, depth, and mechanism do not indicate tsunamigenic potential according to INCOIS.\n\n📍 Mainland South India: No impact expected. This is a seismically active subduction zone and M4.5–5.5 earthquakes are common in this region.\n\n🔬 <i>TerranovaX seismic monitoring network · Data verified with NCS India · Updated 15 minutes post-event</i>"
            },
            {
                "id": "is_09", "type": "green",
                "location": "Kerala / Western Ghats",
                "text": "✅ <b>Biodiversity Pulse — Western Ghats</b>\n\nSatellite analysis of the Western Ghats biodiversity hotspot this month shows a 6.2% increase in vegetation density compared to last year — one of the strongest green recovery signals recorded in the past decade.\n\n🌿 The above-normal rainfall received in Kerala and Karnataka has significantly replenished forest cover and restored stream flow in 14 major river tributaries.\n\n🦋 Wildlife corridors between Anamalai Tiger Reserve and Parambikulam appear more actively used based on thermal imaging, suggesting improved habitat conditions.\n\n🌳 <i>Data: TerranovaX Sentinel-2 satellite analysis · Compared against 2015–2024 baseline</i>"
            },
            {
                "id": "is_10", "type": "brown",
                "location": f"{city}",
                "text": f"⚠️ <b>Thunderstorm Watch — Possible Afternoon Showers</b>\n\nAtmospheric conditions over {city} and surrounding districts are favourable for the development of isolated thunderstorms during afternoon and evening hours (3 PM – 8 PM) today and tomorrow.\n\n⚡ Thunderstorms in the region may bring:\n• Moderate to heavy rainfall (20–40mm in short bursts)\n• Lightning activity\n• Gusty winds (40–50 km/h)\n• Possible localised waterlogging in low-lying areas\n\n🚗 If caught in a thunderstorm while driving, pull over safely and wait it out. Do not park under trees.\n\n🏠 Stay indoors during active lightning. Unplug sensitive electronics.\n\n📡 <i>This is a watch, NOT a warning. Storms may or may not materialise.</i>"
            },
            {
                "id": "is_11", "type": "green",
                "location": "Chennai / Tamil Nadu Coast",
                "text": "✅ <b>Ocean Temperature & Marine Health Update</b>\n\nSea Surface Temperatures (SST) along the Tamil Nadu and Andhra coastline are in the 28–30°C range this week — within the normal seasonal average. There are no signs of unusual warming or marine heat wave conditions at this time.\n\n🐟 Marine fishing conditions: Moderate to good. Visibility at 6–8m in most coastal zones. Wave heights 1–1.5m, suitable for near-shore fishing.\n\n🌊 Coral reef monitoring at Palk Bay and Gulf of Mannar: Bleaching stress index LOW. Recent rainfall and lower temperatures have reduced bleaching risk compared to last month.\n\n🐠 <i>Source: INCOIS Ocean State Forecast · TerranovaX Marine Sensor Array</i>"
            },
            {
                "id": "is_12", "type": "brown",
                "location": "South India",
                "text": "⚠️ <b>Dengue Risk Advisory — Monsoon Season</b>\n\nWith the monsoon bringing standing water in many areas, the risk of vector-borne diseases including dengue and malaria is elevated across South India through October.\n\n🦟 TerranovaX environmental risk model rates dengue transmission potential as MODERATE-HIGH for urban areas with poor drainage in Tamil Nadu, Andhra Pradesh, and Karnataka.\n\n🏡 Prevent mosquito breeding at home:\n• Empty and clean all water containers weekly (coolers, flower pots, tyres)\n• Use mosquito nets and repellent during dawn/dusk\n• Wear full-sleeve clothing in evenings\n• Report stagnant water accumulation to local civic bodies\n\n💊 Seek medical care immediately if you develop sudden high fever with joint/muscle pain.\n\n📊 <i>Environmental health advisory · Not a disease outbreak alert</i>"
            },
        ]

    elif region == "india_north":
        return [
            {
                "id": "in_01", "type": "green",
                "location": f"{city}, North India",
                "text": f"✅ <b>Pre-Monsoon Showers Bring Relief to {city}</b>\n\nA western disturbance interacting with moisture from the Arabian Sea brought welcome pre-monsoon showers to {city} and parts of north India last night. Rainfall recorded: 18mm in 3 hours.\n\n🌡️ Temperatures have dropped by 5–7°C from yesterday's peak. Current conditions: 33°C (down from 41°C yesterday) · Humidity: 58%.\n\n🌬️ Air quality has improved sharply — AQI dropped from 142 to 78 following the rain. Cooler, cleaner air expected through tomorrow morning.\n\n💧 Groundwater recharge: Early monsoon rains have begun replenishing the water table in Haryana and western UP aquifer zones.\n\n📡 <i>TerranovaX regional sensor data · IMD pre-monsoon bulletin</i>"
            },
            {
                "id": "in_02", "type": "green",
                "location": "Delhi NCR",
                "text": "✅ <b>Delhi Air Quality — Moderate (Improving)</b>\n\nDelhi NCR's AQI stands at 94 today — in the 'Moderate' category and significantly better than last month's chronic poor air days. Favorable southwest winds are flushing out pollutants.\n\n📊 Station-wise readings:\n• ITO: 88 (Moderate) · Lodhi Road: 71 (Good)\n• Anand Vihar: 112 (Moderate) · RK Puram: 99 (Moderate)\n\n🌬️ The onset of the southwest monsoon branch into Punjab and Haryana is bringing cleaner, moisture-laden air into the Delhi airshed. Forecast: AQI to remain below 100 for the next 4 days.\n\n🚲 Good conditions for outdoor activities early morning (6–9 AM).\n\n📡 <i>CPCB monitoring network · TerranovaX air quality analytics</i>"
            },
            {
                "id": "in_03", "type": "brown",
                "location": f"{city} / North India",
                "text": f"⚠️ <b>Heat Advisory — Above-Normal Temperatures</b>\n\nTemperatures in {city} are running 3–4°C above the seasonal normal this week. Forecast peak: 43°C tomorrow afternoon. The heat index (factoring humidity) will make it feel like 47°C in exposed areas.\n\n🌡️ This is an advisory, not a red heat wave alert — temperatures are elevated but within the range expected for this time of year in North India.\n\n💧 Precautions:\n• Drink water regularly — don't wait until thirsty\n• Avoid outdoor work during 11 AM – 4 PM if possible\n• Wear light-coloured, breathable clothing\n• Watch for signs of heat exhaustion: dizziness, nausea, heavy sweating\n\n📞 Heat emergency: 108 · PMO helpline: 1800-11-4000\n\n📊 <i>IMD seasonal normal comparison · TerranovaX heat dome analysis</i>"
            },
            {
                "id": "in_04", "type": "brown",
                "location": "Himachal Pradesh / Uttarakhand",
                "text": "⚠️ <b>Mountain Advisory — Landslide-Prone Zones Active</b>\n\nContinued rainfall over the past week has saturated slopes in Himachal Pradesh and Uttarakhand. The Geological Survey of India flags 11 high-sensitivity zones currently on yellow watch — meaning elevated (not imminent) landslide risk.\n\n🏔️ Affected routes: NH-5 (Shimla–Kinnaur), NH-707 (Mandi area), Kedarnath motor road (seasonal caution).\n\n🚗 If travelling to hill districts: Check local authority road clearance updates before departing. Never park vehicles near steep embankments or river banks during rain.\n\n⛺ Trekkers: Inform local authorities of your route and expected return. Avoid camping near cliff bases or narrow gorges.\n\n📡 <i>GSI slope stability monitoring · TerranovaX Himalayan terrain analysis</i>"
            },
            {
                "id": "in_05", "type": "red",
                "location": "Rajasthan / MP",
                "text": "🚨 <b>Red Heat Wave Alert — Rajasthan & Madhya Pradesh</b>\n\nIMD has issued a Red Heat Wave Alert for 12 districts in Rajasthan and 6 in Madhya Pradesh. Temperatures in Churu, Bikaner, and Barmer forecast to exceed 48°C tomorrow — potentially breaking station records.\n\n😓 This is a life-threatening event:\n• Heat stroke risk is VERY HIGH for outdoor workers, elderly, and children under 5\n• Avoid all non-essential outdoor activity between 10 AM and 6 PM\n\n🏥 Cooling centres open across all municipal areas. If you see someone collapsed from heat:\n→ Move to shade/cool area immediately\n→ Apply cool water to skin, fan continuously\n→ Call 108 immediately — heat stroke is a medical emergency\n\n💧 Hydrate: minimum 3 litres water daily. Add ORS if sweating heavily.\n\n📊 <i>IMD Red Alert issued · 12 districts under emergency heat protocol</i>"
            },
            {
                "id": "in_06", "type": "red",
                "location": "Uttarakhand",
                "text": "🚨 <b>Cloudburst Alert — Chamoli & Rudraprayag</b>\n\nTerranovaX atmospheric sensors detected a cloudburst event near Chamoli district at 11:20 PM last night, dumping 94mm of rainfall in under 2 hours. Flash flooding in the Alaknanda and Mandakini tributaries is ongoing.\n\n⚠️ Current situation:\n• Badrinath highway (NH-58) blocked near Pandukeshwar — clearance operations underway\n• Kedarnath base camp: All clear, no impact reported\n• 2 small bridges on secondary roads washed out in Rudraprayag district\n\n🆘 If you are in a flood-affected area: Move to upper floors or higher ground. Call State Emergency: 1070 · NDRF: 0120-2309452\n\n📡 <i>TerranovaX cloudburst detection triggered 8 minutes after event onset · Satellite confirmation at 11:35 PM</i>"
            },
            {
                "id": "in_07", "type": "green",
                "location": "Punjab / Haryana",
                "text": "✅ <b>Monsoon Onset — Punjab & Haryana</b>\n\nThe IMD has officially declared the onset of the Southwest Monsoon over Punjab, Haryana, and Delhi — 5 days ahead of the normal date of June 29. This marks one of the earliest monsoon arrivals in the northern plains in the last 15 years.\n\n🌧️ Rainfall recorded in the last 24 hours:\n• Amritsar: 38mm · Ludhiana: 44mm · Chandigarh: 31mm · Gurgaon: 28mm\n\n🌾 Early monsoon is excellent news for kharif sowing. Paddy and cotton cultivation expected to pick up pace rapidly.\n\n🌡️ Temperatures have dropped 6–9°C across the Punjab plains. Maximum in Amritsar: 31°C, down from 40°C on Monday.\n\n📡 <i>IMD onset declaration · TerranovaX monsoon tracking system</i>"
            },
            {
                "id": "in_08", "type": "brown",
                "location": "Ganga Plains",
                "text": "⚠️ <b>River Watch — Ganga & Brahmaputra Basin</b>\n\nFollowing above-normal rainfall in the upper Himalayas, water levels in the Ganga are rising at Haridwar, Kanpur, and Prayagraj — currently flowing at 65–72% of danger level. No flood threat at present, but TerranovaX is monitoring.\n\n🌊 Brahmaputra at Guwahati: 78% of danger mark. Assam State Disaster Management Authority has put 12 riverside districts on yellow alert as a precaution.\n\n📍 Areas to watch over the next 72 hours:\n• Kaziranga National Park buffer zone\n• Majuli Island (Assam)\n• Lower districts of Bihar along the Kosi river\n\n📡 <i>Central Water Commission river gauging data · TerranovaX flood prediction model updated every 6 hours</i>"
            },
            {
                "id": "in_09", "type": "green",
                "location": "North India",
                "text": "✅ <b>Wheat Harvest Season — Climate Conditions Favourable</b>\n\nClimate conditions across North India's wheat belt (Punjab, Haryana, UP, Rajasthan) remained largely favourable during the critical grain-filling period this season. TerranovaX crop stress analysis shows only 4% of wheat acreage experienced climate-related stress, compared to 19% last year.\n\n🌾 ICAR's early estimate: Wheat production could touch 115 million tonnes — a potential record, pending final harvest data.\n\n🌡️ Post-harvest, fields are transitioning to Kharif crops. Soil moisture levels are adequate in most districts for direct-seeded paddy and cotton sowing.\n\n📊 <i>TerranovaX AgriWatch · Satellite-derived crop health index · ICAR estimates</i>"
            },
            {
                "id": "in_10", "type": "brown",
                "location": f"{city}",
                "text": f"⚠️ <b>Dust Storm Watch — {city} Region</b>\n\nAtmospheric conditions are favourable for dust storm development across {city} and the western Rajasthan plains late this evening. Pre-monsoon convection combined with strong surface winds (40–60 km/h) could generate dust lifting events.\n\n🌪️ Expected visibility: May drop to 500m or less during active dust events. Duration: typically 30–90 minutes per event.\n\n✈️ Air travellers: Check flight status before heading to the airport. Ground stops are possible during active dust.\n\n🚗 Drivers: Switch on headlights and reduce speed during dust. Pull over safely if visibility drops below 50m.\n\n🏠 Close all windows and doors. Cover water storage containers. Keep children and elderly indoors.\n\n📡 <i>Dust storm watch — not a confirmed storm warning. Conditions are favourable, not certain.</i>"
            },
        ]

    elif region == "india_west":
        return [
            {
                "id": "iw_01", "type": "green",
                "location": "Mumbai / Maharashtra Coast",
                "text": "✅ <b>Mumbai Monsoon — On Track</b>\n\nThe Southwest Monsoon over Mumbai and coastal Maharashtra is progressing normally this season. Seasonal rainfall stands at 96% of LPA — essentially on track. Reservoirs supplying Mumbai (Tansa, Vihar, Tulsi, Upper Vaitarna) are collectively at 81% capacity — well ahead of last year's 67%.\n\n🌧️ The city has not experienced any extreme rainfall events (>200mm/day) this month, which has kept waterlogging incidents lower than average.\n\n🚇 Mumbai local train services have been running without major weather-related disruptions for the past 12 days — one of the better recent monsoon performances.\n\n📡 <i>IMD Mumbai bulletin · MCGM reservoir levels · TerranovaX urban rainfall analysis</i>"
            },
            {
                "id": "iw_02", "type": "green",
                "location": "Goa / Konkan",
                "text": "✅ <b>Konkan Coast — Marine Conditions Update</b>\n\nSea conditions along the Goa–Konkan coastline have moderated following last week's rough seas. Current wave heights: 1.2–1.8m. Wind speeds: 25–35 km/h. Conditions suitable for near-shore fishing from tomorrow.\n\n🐟 Fishing community update: The mandatory monsoon fishing ban in Maharashtra has been lifted for mechanised vessels. Karnataka ban remains in effect until August 1.\n\n🏖️ Beach safety: Rip currents remain a risk at exposed beaches. Swim only at designated lifeguard-patrolled zones. Red flags at Palolem, Arambol, and Calangute — swimming prohibited.\n\n☁️ Forecast: Intermittent showers, occasional heavy spells. This is normal for peak monsoon Konkan — not a concern.\n\n📡 <i>INCOIS coastal forecast · TerranovaX Konkan marine monitor</i>"
            },
            {
                "id": "iw_03", "type": "brown",
                "location": f"{city} / Gujarat",
                "text": f"⚠️ <b>Arabian Sea Monitoring — Low-Pressure System</b>\n\nTerranovaX satellites are tracking a low-pressure area in the northeast Arabian Sea approximately 680km west of the Gujarat coast. At this time, the system is weak and disorganised.\n\n🌀 Wind speeds near center: 30–35 km/h · Sea state: Moderate\n\n📊 Current model consensus does NOT show this system intensifying significantly. Wind shear conditions are unfavourable for development. However, it may bring:\n• Increased cloud cover over Gujarat and Mumbai\n• Rough seas along the Gujarat coast\n• Possible heavy rainfall in Saurashtra if the system moves eastward\n\n⛵ Fishermen: Avoid waters beyond 60km from the coast until this system dissipates.\n\n📡 <i>Monitoring continues · Next assessment in 6 hours · No alert issued at this time</i>"
            },
            {
                "id": "iw_04", "type": "brown",
                "location": "Maharashtra",
                "text": "⚠️ <b>Orange Rain Alert — Vidarbha Region</b>\n\nThe IMD has issued an Orange alert (heavy to very heavy rainfall) for 6 districts in Vidarbha: Chandrapur, Gadchiroli, Yavatmal, Amravati, Washim, and Akola over the next 48 hours.\n\n🌧️ Rainfall expected: 65–115mm in 24 hours at some stations. This is in the heavy category but NOT extreme.\n\n📍 Potential impacts:\n• Localised waterlogging in low-lying residential areas\n• Agricultural fields may see temporary standing water (not damaging for most crops)\n• Possible minor overflow in small rivulets and nullahs\n\n🚗 Avoid driving through flooded roads — even 30cm of water can stall a car.\n\n📊 <i>Orange alert issued — precautionary. Not the same as a flood warning. Typical monsoon conditions for Vidarbha in this season.</i>"
            },
            {
                "id": "iw_05", "type": "red",
                "location": "Gujarat Coast",
                "text": "🚨 <b>Cyclone Alert — Arabian Sea System Intensifying</b>\n\nA depression in the northeast Arabian Sea has rapidly intensified into a cyclonic storm. Maximum sustained winds are now 85 km/h with gusts to 100 km/h. The system is tracking northeast toward the Saurashtra–Kutch coastline.\n\n🌀 Expected landfall: 36–48 hours · Storm surge: 1.5–2.5m above normal tide predicted for Kutch and Jamnagar districts.\n\n🏠 Mandatory evacuation ordered for:\n• All residents within 1km of coastline in Kutch, Porbandar, Jamnagar, Junagarh, Amreli districts\n• Low-lying areas below 3m elevation in coastal talukas\n\n📦 Evacuation kit: 5 days food & water · Important documents · Medications · Torch & batteries · Cash · Power bank\n\n📞 Gujarat SDMA: 1070 · NDRF: 0120-2309452 · Relief Commissioner: 079-23251900"
            },
            {
                "id": "iw_06", "type": "red",
                "location": "Mumbai",
                "text": "🚨 <b>Extreme Rainfall — Mumbai Red Alert</b>\n\nIMD has issued a Red Alert for Mumbai, Thane, Raigad, and Palghar for the next 24 hours. A strong low-level jet stream is directing intense moisture into the Konkan coast, triggering exceptionally heavy rainfall.\n\n🌧️ Recorded in last 6 hours: Colaba 87mm · Santa Cruz 103mm · Thane 118mm\n\n⚠️ Impacts being reported:\n• Waterlogging at Hindmata, Sion, Kurla, Vikhroli\n• Mumbai Central–Dadar slow section: local trains running 15 min late\n• BMC pumping stations at full capacity in Parel, Dharavi\n\n🚫 Avoid:\n• Low-lying areas and flooded underpasses — NEVER drive through them\n• Travelling unless essential\n• Coastal areas and beaches\n\n🏠 Work from home if possible today.\n\n📞 BMC Disaster: 1916 · NDRF Mumbai: 022-26120020"
            },
            {
                "id": "iw_07", "type": "green",
                "location": f"{city} / West India",
                "text": f"✅ <b>Air Quality — {city}: Moderate (Improving)</b>\n\nAQI in {city} stands at 82 today — 'Moderate' and improving. Monsoon winds from the southwest are clearing industrial pollutants from the region.\n\n🌬️ Major pollutant: PM10 (dust from construction activity). PM2.5 is within safe limits.\n\n🌱 Sensitive groups (asthma, heart conditions): Consider reducing extended outdoor exercise. General population: Normal outdoor activity is fine.\n\n📊 Forecast: AQI expected to drop further to the 'Good' category by Thursday as monsoon strengthens.\n\n🏃 Best time for outdoor exercise: Early morning 6–8 AM when temperatures are lower and pollution dispersion is better.\n\n📡 <i>CPCB stations data · TerranovaX air quality model for West India</i>"
            },
            {
                "id": "iw_08", "type": "brown",
                "location": "Western Ghats — Maharashtra / Goa",
                "text": "⚠️ <b>Ghat Road Advisory — Reduced Visibility</b>\n\nHeavy monsoon rainfall on the Western Ghats is causing frequent low cloud, fog patches, and reduced visibility on ghat roads including:\n• Mumbai–Pune Expressway (Khopoli–Khandala section)\n• NH-48 through Bhor Ghat\n• Amboli Ghat, Tamhini Ghat, Malshej Ghat\n\n🚗 Driving safety on ghat roads:\n• Switch on headlights and hazard lights in foggy stretches\n• Maintain 30 km/h max in blind curves\n• Do NOT overtake on ghat sections\n• Watch for loose rock and waterfall runoff crossing the road\n\n🏍️ Motorcyclists: Particularly high risk on wet ghat roads. Consider delaying your journey.\n\n📡 <i>Maharashtra Traffic Police advisory · TerranovaX ghat road safety monitor</i>"
            },
        ]

    elif region == "southeast_asia":
        return [
            {
                "id": "sea_01", "type": "green",
                "location": f"{city} / SE Asia",
                "text": f"✅ <b>ENSO Neutral — Reduced Extreme Weather Risk</b>\n\nThe ENSO (El Niño–Southern Oscillation) index has returned to neutral conditions after 14 months of El Niño. This is broadly good news for Southeast Asia — neutral ENSO years typically see near-normal rainfall distribution across the region.\n\n🌧️ WMO forecasts suggest a 55% probability of La Niña developing by mid-year, which would further enhance monsoon rainfall across mainland Southeast Asia.\n\n🌾 Agricultural outlook: Rice cultivation in Thailand, Vietnam, and Myanmar is expected to benefit from improved water availability. Indonesia's dry season is forecast to be shorter than last year's El Niño-affected season.\n\n📡 <i>WMO ENSO Update · APEC Climate Center · TerranovaX regional climate model</i>"
            },
            {
                "id": "sea_02", "type": "brown",
                "location": "Western Pacific",
                "text": "⚠️ <b>Tropical Disturbance — Western Pacific</b>\n\nA tropical disturbance (Invest 93W) has formed in the western Pacific near Micronesia. At this stage it is a disorganised cluster of convection with only a 30% probability of developing into a tropical cyclone within the next 48 hours.\n\n🌀 Current location: 8°N, 148°E — well east of the Philippines. If development occurs, the most likely track is northwest toward the Philippines, but there is very high uncertainty at this early stage.\n\n📊 TerranovaX will issue an alert immediately if this system strengthens and a track toward populated coastlines becomes more likely.\n\n📡 <i>JTWC tropical weather outlook · TerranovaX Pacific tropical monitor</i>"
            },
            {
                "id": "sea_03", "type": "red",
                "location": "Philippines",
                "text": "🚨 <b>Typhoon Warning — Philippines</b>\n\nTyphoon signal warnings have been raised across multiple Philippine provinces as a Category 3 typhoon approaches from the Pacific. Maximum sustained winds: 175 km/h · Gusts to 215 km/h.\n\n🌀 Projected landfall: Aurora–Quezon province coastline within 12–18 hours.\n\n🚨 PAGASA Signal Warnings raised:\n• Signal #4 (extremely dangerous): 3 provinces\n• Signal #3 (very destructive): 12 provinces\n• Signal #2 (destructive): 18 provinces\n\n🏠 MANDATORY EVACUATION for all residents in coastal and low-lying areas in affected provinces. Move to nearest designated evacuation centre NOW.\n\n📞 NDRRMC Operations Centre: 911 | Red Cross: 143 | Coast Guard: 5100\n\n📡 <i>PAGASA official advisory · JTWC TC bulletin · TerranovaX real-time track</i>"
            },
            {
                "id": "sea_04", "type": "brown",
                "location": "Southeast Asia",
                "text": "⚠️ <b>Haze Advisory — Sumatra / Borneo Fire Season</b>\n\nSatellite hotspot detection is showing elevated fire activity in parts of South Sumatra and Central Kalimantan as the dry season begins. Smoke from peatland fires is causing localised haze in parts of Singapore, southern Malaysia, and western Indonesia.\n\n🌫️ Current PSI/AQI readings:\n• Singapore: PSI 88 (Moderate) — normal precautions advised\n• Kuala Lumpur: API 95 (Moderate)\n• Palembang, South Sumatra: AQI 145 (Unhealthy for Sensitive Groups)\n\n😷 If outdoors in haze-affected areas: Wear N95 masks, keep windows closed, run air purifiers.\n\n📡 <i>ASEAN Specialised Meteorological Centre haze monitoring · TerranovaX fire hotspot satellite analysis</i>"
            },
            {
                "id": "sea_05", "type": "green",
                "location": f"{city} / SE Asia",
                "text": f"✅ <b>Air Quality — {city}: Good</b>\n\nCurrent air quality in {city} is in the Good category (AQI: 42). Prevailing winds from the South China Sea are keeping pollution levels low.\n\n🌤️ Weather: Partly cloudy, 29–32°C, afternoon showers possible. UV Index: Very High (9) — apply SPF 50+ sunscreen for outdoor activities.\n\n🌊 Sea conditions: 1.0–1.5m swell, light winds. Suitable for recreational water activities at most resort beaches.\n\n🌿 Vegetation Health Index across {city} region: EXCELLENT — above the 5-year average, reflecting good monsoon performance this year.\n\n📡 <i>TerranovaX SE Asia regional air quality and weather monitor</i>"
            },
        ]

    else:
        return [
            {
                "id": "gl_01", "type": "green",
                "location": "Global",
                "text": "✅ <b>Global Renewables Milestone — Record Solar Output</b>\n\nGlobal solar power generation crossed 2,000 TWh for the first time in a 12-month period, according to the International Energy Agency. This is equivalent to the annual electricity consumption of India.\n\n⚡ Solar now accounts for 8.3% of global electricity generation — up from 3.6% just five years ago. Combined with wind (7.8%), renewables now supply 16.1% of the world's electricity.\n\n🌍 Carbon emissions from the power sector declined by 4.2% this year — the steepest single-year drop since the COVID-19 disruption in 2020, but this time driven by clean energy rather than economic slowdown.\n\n📊 <i>IEA Electricity Market Report · TerranovaX climate data compilation</i>"
            },
            {
                "id": "gl_02", "type": "brown",
                "location": "East Africa",
                "text": "⚠️ <b>Drought Advisory — Horn of Africa</b>\n\nThe Greater Horn of Africa is experiencing its fifth consecutive below-normal rainy season. TerranovaX satellite analysis shows soil moisture deficits of 35–50% across large parts of Somalia, Ethiopia, and northern Kenya.\n\n🌵 The drought is particularly severe in pastoral areas where livestock mortality has exceeded 2.1 million animals, destroying livelihoods for hundreds of thousands of families.\n\n💧 Water stress index for the region: CRITICAL in 42% of monitored zones.\n\n🌍 WFP and OCHA have classified 18 million people in the region as facing acute food insecurity. International humanitarian response is ongoing but underfunded.\n\n📡 <i>FEWS NET drought monitor · UN-OCHA situation report · TerranovaX vegetation and soil moisture analysis</i>"
            },
            {
                "id": "gl_03", "type": "red",
                "location": "Mediterranean",
                "text": "🚨 <b>Extreme Wildfire Risk — Mediterranean Basin</b>\n\nAn exceptional heat dome has parked over the central and eastern Mediterranean, driving temperatures 8–12°C above seasonal average across Greece, Turkey, Italy, and southern Spain. Combined with months of drought-dried vegetation, the wildfire risk index has reached EXTREME across the region.\n\n🔥 Active fires reported in:\n• Evros, Greece: 3,400 hectares burned, 4 villages evacuated\n• Antalya, Turkey: 1,800 hectares, 2 resorts under threat\n• Sicily, Italy: Multiple small fires, 2 merged into one 600-hectare blaze\n\n✈️ If travelling to affected areas: Register your whereabouts with hotel or local authorities. Know your evacuation route.\n\n📡 <i>Copernicus EFFIS wildfire system · TerranovaX Mediterranean heat and fire monitor</i>"
            },
            {
                "id": "gl_04", "type": "red",
                "location": "Global Seismic",
                "text": "🚨 <b>Significant Earthquake — Southern Turkey</b>\n\nA M 6.2 earthquake struck 45km east of Gaziantep, Turkey at 03:14 UTC today. The quake was felt across a wide area including northern Syria, Lebanon, and Cyprus. Depth: 14km (shallow, meaning stronger surface shaking).\n\n🏗️ Reports of structural damage to older buildings in Gaziantep and Kilis districts. AFAD (Turkish Disaster Agency) has mobilised 14 urban search and rescue teams.\n\n🌊 No tsunami threat from this event — confirmed by regional tsunami centres.\n\n📡 <i>USGS ShakeMap · EMSC EMS-98 intensity report · TerranovaX rapid damage assessment model</i>"
            },
            {
                "id": "gl_05", "type": "green",
                "location": "Antarctica",
                "text": "✅ <b>Antarctic Ice Shelf — East Sector Stability Confirmed</b>\n\nNew analysis of ICESat-2 altimetry data confirms that the East Antarctic Ice Sheet — which holds 90% of Antarctic ice — remains stable and is slightly gaining mass from snowfall (+67 Gt/year). This is consistent with climate models.\n\n❄️ However, the opposite pattern is occurring in West Antarctica: Pine Island and Thwaites glaciers continue their accelerating retreat. Thwaites alone could raise global sea levels by 65cm if it collapsed — though current models suggest this over centuries, not decades.\n\n🌊 Net contribution to sea level from all ice sheets combined: approximately +1.8mm/year.\n\n📊 <i>NASA/CNES ICESat-2 mission · TerranovaX cryosphere monitoring summary</i>"
            },
            {
                "id": "gl_06", "type": "brown",
                "location": "Pacific Ocean",
                "text": "⚠️ <b>La Niña Watch — Pacific Ocean Conditions</b>\n\nNOAA and the Bureau of Meteorology have issued a La Niña Watch, indicating a 60% probability that La Niña conditions will develop in the Pacific Ocean by August–September.\n\n🌊 What this means for different regions:\n• Southeast Asia & Australia: WETTER than normal — increased flood risk during monsoon\n• Horn of Africa: DRIER — drought risk worsens\n• South America (Andes): WETTER — enhanced Altiplano rainfall\n• Southern USA: DRIER and warmer — elevated wildfire and drought risk\n• Indian Ocean: Warmer SSTs favourable for above-normal Indian monsoon\n\n📊 La Niña events typically last 9–12 months. Full development confirmation expected by September.\n\n📡 <i>NOAA Climate Prediction Center · BOM ENSO Outlook · TerranovaX global climate trend analysis</i>"
            },
        ]


def detect_region(lat, lon):
    """Detect broad geographic region from coordinates."""
    if lat is None or lon is None:
        return "global"

    # India South (Tamil Nadu, Kerala, Karnataka, Andhra, Telangana)
    if 8 <= lat <= 16 and 72 <= lon <= 84:
        return "india_south"

    # India West (Gujarat, Maharashtra, Goa)
    if 15 <= lat <= 25 and 68 <= lon <= 78:
        return "india_west"

    # India North (Delhi, UP, Rajasthan, Haryana, Punjab, Himachal, Uttarakhand)
    if 23 <= lat <= 37 and 70 <= lon <= 92:
        return "india_north"

    # Southeast Asia
    if -5 <= lat <= 28 and 95 <= lon <= 145:
        return "southeast_asia"

    return "global"


# ── ROUTE: Handle Reactions ──
@app.route("/api/react", methods=["POST"])
def react():
    data     = request.json or {}
    post_id  = data.get("post_id", "")
    reaction = data.get("reaction", "")

    if not post_id or reaction not in ("thumbsUp", "fire", "sad"):
        return jsonify({"error": "Invalid"}), 400

    reactions = load_json(REACTIONS_FILE, {})
    if post_id not in reactions:
        reactions[post_id] = {"thumbsUp": 0, "fire": 0, "sad": 0}

    reactions[post_id][reaction] = reactions[post_id].get(reaction, 0) + 1
    save_json(REACTIONS_FILE, reactions)

    return jsonify(reactions[post_id])


# ── WELCOME EMAIL ──
def send_welcome_email(to_email):
    msg = MIMEMultipart("alternative")
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = to_email
    msg["Subject"] = "🌍 Welcome to TerranovaX — You're In!"

    html = """
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#050807;font-family:'Helvetica Neue',Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#050807;">
<tr><td align="center" style="padding:40px 20px;">

<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

  <!-- HEADER -->
  <tr>
    <td style="background:rgba(31,111,67,0.08);border:1px solid rgba(31,111,67,0.2);border-radius:16px 16px 0 0;padding:40px;text-align:center;">
      <div style="font-size:48px;margin-bottom:12px;">📡</div>
      <div style="font-size:28px;font-weight:700;background:linear-gradient(90deg,#1f6f43,#7a1f2b);-webkit-background-clip:text;color:#1f6f43;">TerranovaX</div>
      <div style="color:#888;font-size:13px;margin-top:6px;letter-spacing:1px;text-transform:uppercase;">Earth Intelligence Network</div>
    </td>
  </tr>

  <!-- BODY -->
  <tr>
    <td style="background:rgba(20,20,20,0.8);border-left:1px solid rgba(31,111,67,0.15);border-right:1px solid rgba(31,111,67,0.15);padding:40px;">

      <h2 style="color:#ffffff;font-size:22px;margin:0 0 16px;">Welcome to the Community 🌏</h2>

      <p style="color:#c0c8c0;font-size:15px;line-height:1.7;margin:0 0 24px;">
        You've joined <strong style="color:#4caf7d;">TerranovaX</strong> — a real-time Earth intelligence platform monitoring climate, disasters, and environmental events across the planet.
      </p>

      <!-- WHAT YOU GET -->
      <div style="background:rgba(31,111,67,0.08);border-left:3px solid #1f6f43;border-radius:0 8px 8px 0;padding:20px 24px;margin-bottom:24px;">
        <div style="color:#4caf7d;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;">What You'll Receive</div>
        <div style="color:#b0b8b0;font-size:14px;line-height:1.8;">
          📍 <strong style="color:#d2d8d2;">Location-based alerts</strong> — real-time climate and disaster updates for your area<br>
          📊 <strong style="color:#d2d8d2;">Weekly Earth Briefing</strong> — every Sunday, your full climate report for the past 7 days<br>
          🔮 <strong style="color:#d2d8d2;">Next-week forecast</strong> — AI-predicted climate events and risk zones<br>
          🛰️ <strong style="color:#d2d8d2;">Satellite insights</strong> — exclusive imagery analysis from our monitoring network
        </div>
      </div>

      <!-- LIVE CHANNEL CTA -->
      <div style="text-align:center;margin:32px 0;">
        <a href="http://yourwebsite.com/channel.html" style="display:inline-block;background:#1f6f43;color:white;text-decoration:none;padding:14px 36px;border-radius:8px;font-size:15px;font-weight:700;letter-spacing:0.3px;">
          Visit Live Channel →
        </a>
        <div style="color:#555;font-size:12px;margin-top:10px;">See real-time alerts for your location</div>
      </div>

      <!-- DIVIDER -->
      <div style="height:1px;background:linear-gradient(90deg,transparent,rgba(31,111,67,0.4),transparent);margin:24px 0;"></div>

      <!-- TODAY'S SNAPSHOT -->
      <div style="color:#888;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:14px;">Today's Earth Snapshot</div>

      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td width="33%" style="padding:0 6px 0 0;">
            <div style="background:rgba(31,111,67,0.08);border:1px solid rgba(31,111,67,0.2);border-radius:8px;padding:14px;text-align:center;">
              <div style="font-size:20px;font-weight:700;color:#4caf7d;">424.8</div>
              <div style="font-size:11px;color:#888;margin-top:4px;">CO₂ ppm</div>
            </div>
          </td>
          <td width="33%" style="padding:0 3px;">
            <div style="background:rgba(122,31,43,0.08);border:1px solid rgba(122,31,43,0.2);border-radius:8px;padding:14px;text-align:center;">
              <div style="font-size:20px;font-weight:700;color:#ff8a8a;">+1.48°C</div>
              <div style="font-size:11px;color:#888;margin-top:4px;">Temp Anomaly</div>
            </div>
          </td>
          <td width="33%" style="padding:0 0 0 6px;">
            <div style="background:rgba(138,109,59,0.08);border:1px solid rgba(138,109,59,0.2);border-radius:8px;padding:14px;text-align:center;">
              <div style="font-size:20px;font-weight:700;color:#d4a85a;">103.6mm</div>
              <div style="font-size:11px;color:#888;margin-top:4px;">Sea Level Rise</div>
            </div>
          </td>
        </tr>
      </table>

    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="background:rgba(10,10,10,0.9);border:1px solid rgba(31,111,67,0.1);border-radius:0 0 16px 16px;padding:24px;text-align:center;">
      <div style="color:#555;font-size:12px;line-height:1.7;">
        You received this because you subscribed to TerranovaX.<br>
        © 2025 TerranovaX — Real-time Earth Intelligence
      </div>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>
"""
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())


# ── WEEKLY NEWSLETTER ──
# Call this from a scheduler (e.g. cron job, APScheduler) every Sunday.
# Or trigger manually via: POST /send-weekly-newsletter
@app.route("/send-weekly-newsletter", methods=["POST"])
def send_weekly_newsletter():
    subscribers = load_json(SUBSCRIBERS_FILE, [])
    sent = 0
    for sub in subscribers:
        try:
            send_weekly_email(sub["email"])
            sent += 1
        except Exception as e:
            print(f"Failed for {sub['email']}: {e}")
    return jsonify({"sent": sent, "total": len(subscribers)})


def send_weekly_email(to_email):
    from datetime import date
    week_start = (date.today() - timedelta(days=7)).strftime("%B %d")
    week_end   = date.today().strftime("%B %d, %Y")

    msg = MIMEMultipart("alternative")
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = to_email
    msg["Subject"] = f"🌍 TerranovaX Weekly Earth Report — {week_start} to {week_end}"

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#050807;font-family:'Helvetica Neue',Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#050807;">
<tr><td align="center" style="padding:40px 20px;">
<table width="620" cellpadding="0" cellspacing="0" style="max-width:620px;width:100%;">

  <!-- HEADER -->
  <tr>
    <td style="background:linear-gradient(135deg,rgba(31,111,67,0.15),rgba(122,31,43,0.15));border:1px solid rgba(31,111,67,0.2);border-radius:16px 16px 0 0;padding:44px 40px;text-align:center;">
      <div style="font-size:40px;margin-bottom:10px;">🌍</div>
      <div style="font-size:13px;letter-spacing:2px;text-transform:uppercase;color:#4caf7d;font-weight:600;margin-bottom:8px;">WEEKLY EARTH REPORT</div>
      <div style="font-size:28px;font-weight:700;color:white;">TerranovaX Briefing</div>
      <div style="color:#666;font-size:13px;margin-top:8px;">{week_start} — {week_end}</div>
    </td>
  </tr>

  <!-- BODY -->
  <tr>
    <td style="background:rgba(15,15,15,0.95);border-left:1px solid rgba(31,111,67,0.12);border-right:1px solid rgba(31,111,67,0.12);padding:40px;">

      <p style="color:#b0b8b0;font-size:15px;line-height:1.7;margin:0 0 32px;">
        Hello Earth Watcher 👋 — Here's your complete climate and disaster intelligence briefing for the past week, plus what our AI models are predicting for the week ahead.
      </p>

      <!-- SECTION: THIS WEEK -->
      <div style="color:#4caf7d;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-bottom:16px;">⚡ THIS WEEK'S TOP EVENTS</div>

      <!-- Event 1 -->
      <div style="background:rgba(122,31,43,0.08);border-left:3px solid #7a1f2b;border-radius:0 8px 8px 0;padding:18px 20px;margin-bottom:14px;">
        <div style="color:#ff8a8a;font-size:12px;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;margin-bottom:6px;">🚨 ALERT — Cyclone Activity</div>
        <div style="color:#d2d8d2;font-size:14px;line-height:1.65;">
          A well-marked low-pressure area over the Bay of Bengal intensified into a cyclonic storm this week, affecting coastal Andhra Pradesh and Tamil Nadu. Storm surge of 1.5–2m above normal tide was recorded. Total displacement: ~85,000 persons. NDRF teams deployed; situation now stabilising.
        </div>
      </div>

      <!-- Event 2 -->
      <div style="background:rgba(138,109,59,0.08);border-left:3px solid #8a6d3b;border-radius:0 8px 8px 0;padding:18px 20px;margin-bottom:14px;">
        <div style="color:#d4a85a;font-size:12px;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;margin-bottom:6px;">⚠️ WARNING — Heat Wave</div>
        <div style="color:#d2d8d2;font-size:14px;line-height:1.65;">
          A severe heat wave persisted over Rajasthan, MP, and Gujarat, with peak temperatures reaching 47.6°C at Churu. The IMD issued red alerts for 9 districts. Heat stroke cases reported: 312 (hospitalised), with local administration opening 840 cooling shelters across 3 states.
        </div>
      </div>

      <!-- Event 3 -->
      <div style="background:rgba(31,111,67,0.08);border-left:3px solid #1f6f43;border-radius:0 8px 8px 0;padding:18px 20px;margin-bottom:28px;">
        <div style="color:#4caf7d;font-size:12px;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;margin-bottom:6px;">✅ UPDATE — Monsoon Progress</div>
        <div style="color:#d2d8d2;font-size:14px;line-height:1.65;">
          The Southwest Monsoon advanced normally this week, covering all of peninsular India and reaching central Maharashtra. Cumulative seasonal rainfall stands at 106% of LPA — an above-normal season. Reservoir levels across 91 major dams at 72% capacity, well above last year's 58%.
        </div>
      </div>

      <!-- GLOBAL VITALS TABLE -->
      <div style="color:#4caf7d;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-bottom:16px;">🌐 GLOBAL EARTH VITALS</div>

      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
        <tr>
          <td style="padding:0 5px 10px 0;" width="33%">
            <div style="background:rgba(31,111,67,0.06);border:1px solid rgba(31,111,67,0.15);border-radius:8px;padding:16px;text-align:center;">
              <div style="color:#4caf7d;font-size:22px;font-weight:700;">424.8</div>
              <div style="color:#888;font-size:11px;margin-top:4px;">CO₂ (ppm)</div>
              <div style="color:#1f6f43;font-size:11px;margin-top:2px;">▲ +2.4 vs last year</div>
            </div>
          </td>
          <td style="padding:0 5px 10px;" width="33%">
            <div style="background:rgba(122,31,43,0.06);border:1px solid rgba(122,31,43,0.15);border-radius:8px;padding:16px;text-align:center;">
              <div style="color:#ff8a8a;font-size:22px;font-weight:700;">+1.48°C</div>
              <div style="color:#888;font-size:11px;margin-top:4px;">Temp Anomaly</div>
              <div style="color:#7a1f2b;font-size:11px;margin-top:2px;">▲ above pre-industrial</div>
            </div>
          </td>
          <td style="padding:0 0 10px 5px;" width="33%">
            <div style="background:rgba(138,109,59,0.06);border:1px solid rgba(138,109,59,0.15);border-radius:8px;padding:16px;text-align:center;">
              <div style="color:#d4a85a;font-size:22px;font-weight:700;">103.6mm</div>
              <div style="color:#888;font-size:11px;margin-top:4px;">Sea Level Rise</div>
              <div style="color:#8a6d3b;font-size:11px;margin-top:2px;">▲ since 1993</div>
            </div>
          </td>
        </tr>
      </table>

      <!-- DIVIDER -->
      <div style="height:1px;background:linear-gradient(90deg,transparent,rgba(31,111,67,0.4),transparent);margin:4px 0 28px;"></div>

      <!-- NEXT WEEK FORECAST -->
      <div style="color:#4caf7d;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-bottom:16px;">🔮 NEXT WEEK — AI FORECAST</div>

      <div style="background:rgba(20,20,20,0.6);border:1px solid rgba(138,109,59,0.2);border-radius:10px;padding:22px;margin-bottom:28px;">
        <div style="color:#d4a85a;font-size:13px;font-weight:600;margin-bottom:12px;">TerranovaX AI Predictions (7-Day Outlook)</div>
        <div style="color:#c0c8c0;font-size:14px;line-height:1.8;">
          🌧️ <strong style="color:#d2d8d2;">Northeast India & Bangladesh</strong> — High probability (78%) of flash flood events in Assam, Meghalaya, Arunachal Pradesh. Brahmaputra river monitoring active.<br><br>
          🌀 <strong style="color:#d2d8d2;">Bay of Bengal</strong> — 55% probability of new low-pressure formation in the western Bay by Wednesday. Could intensify into depression by weekend.<br><br>
          ☀️ <strong style="color:#d2d8d2;">Rajasthan / Gujarat</strong> — Heat wave conditions expected to ease with pre-monsoon showers arriving mid-week. Temperatures to drop 4–6°C by Thursday.<br><br>
          🌊 <strong style="color:#d2d8d2;">Pacific Activity</strong> — Tropical disturbance forming near Micronesia. 40% probability of typhoon development by Day 5. Tracking toward Philippines.
        </div>
      </div>

      <!-- SAFETY TIP -->
      <div style="background:rgba(31,111,67,0.06);border:1px solid rgba(31,111,67,0.15);border-radius:10px;padding:20px 22px;margin-bottom:28px;text-align:center;">
        <div style="color:#4caf7d;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">🛡️ WEEKLY SAFETY REMINDER</div>
        <div style="color:#b0b8b0;font-size:14px;line-height:1.65;font-style:italic;">
          "During monsoon season, never underestimate moving water. Just 15cm of fast-moving water can knock an adult off their feet. 60cm can carry away a vehicle. When in doubt — wait it out."
        </div>
      </div>

      <!-- CTA -->
      <div style="text-align:center;">
        <a href="http://yourwebsite.com/channel.html" style="display:inline-block;background:#1f6f43;color:white;text-decoration:none;padding:14px 36px;border-radius:8px;font-size:15px;font-weight:700;">
          Open Live Channel →
        </a>
        <div style="color:#555;font-size:12px;margin-top:10px;">Real-time alerts based on your location</div>
      </div>

    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="background:rgba(8,8,8,0.98);border:1px solid rgba(31,111,67,0.08);border-radius:0 0 16px 16px;padding:28px 40px;text-align:center;">
      <div style="color:#1f6f43;font-size:14px;font-weight:700;margin-bottom:6px;">TerranovaX</div>
      <div style="color:#555;font-size:12px;line-height:1.7;">
        Real-time Earth Intelligence · Climate & Disaster Monitoring<br>
        You are receiving this weekly briefing as a TerranovaX community member.<br>
        © 2025 TerranovaX — Monitoring Earth, So You Don't Have To.
      </div>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>
"""
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())


if __name__ == "__main__":
    app.run(debug=True)
