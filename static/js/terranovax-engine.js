/**
 * ████████╗███████╗██████╗ ██████╗  █████╗ ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗ ██╗  ██╗
 * ╚══██╔══╝██╔════╝██╔══██╗██╔══██╗██╔══██╗████╗  ██║██╔═══██╗██║   ██║██╔══██╗╚██╗██╔╝
 *    ██║   █████╗  ██████╔╝██████╔╝███████║██╔██╗ ██║██║   ██║██║   ██║███████║ ╚███╔╝
 *    ██║   ██╔══╝  ██╔══██╗██╔══██╗██╔══██║██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║ ██╔██╗
 *    ██║   ███████╗██║  ██║██║  ██║██║  ██║██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║██╔╝ ██╗
 *    ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝╚═╝  ╚═╝
 *
 * TerranovaX Intelligence Engine v1.0
 * 19-System Production-Grade Data Architecture
 * Real-time Climate & Disaster Intelligence
 */

// ═══════════════════════════════════════════════════════════════
// 🧠 1. CENTRAL STATE MANAGEMENT
// Single source of truth for all data
// ═══════════════════════════════════════════════════════════════
const TNXState = {
  weather:     null,
  aqi:         null,
  earthquake:  null,
  forecast:    null,
  city:        null,
  lat:         null,
  lon:         null,
  lastUpdated: null,
  isOnline:    navigator.onLine,
  user:        null,

  set(key, value) {
    this[key] = value;
    TNXEvents.emit("stateChanged", { key, value });
  },

  get(key) {
    return this[key];
  }
};

// ═══════════════════════════════════════════════════════════════
// ⚡ 2. EVENT-DRIVEN SYSTEM
// Loose coupling between all modules
// ═══════════════════════════════════════════════════════════════
const TNXEvents = {
  _events: {},

  on(event, cb) {
    if(!this._events[event]) this._events[event] = [];
    this._events[event].push(cb);
  },

  off(event, cb) {
    if(!this._events[event]) return;
    this._events[event] = this._events[event].filter(fn => fn !== cb);
  },

  emit(event, data) {
    (this._events[event] || []).forEach(cb => {
      try { cb(data); } catch(e) { console.error(`TNX Event error [${event}]:`, e); }
    });
  }
};

// ═══════════════════════════════════════════════════════════════
// ⚙️ 3. SYSTEM HEALTH TRACKING
// Track API success/fail rates + latency
// ═══════════════════════════════════════════════════════════════
const TNXHealth = {
  stats: {
    weather:    { success: 0, fail: 0, lastSync: null, latency: 0 },
    aqi:        { success: 0, fail: 0, lastSync: null, latency: 0 },
    earthquake: { success: 0, fail: 0, lastSync: null, latency: 0 },
    forecast:   { success: 0, fail: 0, lastSync: null, latency: 0 },
  },

  record(source, status, latency = 0) {
    if(!this.stats[source]) this.stats[source] = { success:0, fail:0, lastSync:null, latency:0 };
    if(status === "ok") {
      this.stats[source].success++;
      this.stats[source].lastSync = new Date().toLocaleTimeString();
      this.stats[source].latency  = latency;
    } else {
      this.stats[source].fail++;
    }
    TNXEvents.emit("healthUpdated", { source, status, latency });
  },

  getScore() {
    let total = 0, success = 0;
    Object.values(this.stats).forEach(s => {
      total   += s.success + s.fail;
      success += s.success;
    });
    return total === 0 ? 100 : Math.round((success / total) * 100);
  }
};

// ═══════════════════════════════════════════════════════════════
// 💾 4. TTL CACHE SYSTEM
// Reduce API calls + persist data across page refreshes
// ═══════════════════════════════════════════════════════════════
const TNXCache = {
  set(key, data, ttlMs = 5 * 60 * 1000) {
    try {
      localStorage.setItem("tnx_" + key, JSON.stringify({
        data,
        expiry: Date.now() + ttlMs,
        timestamp: Date.now()
      }));
    } catch(e) { console.warn("TNX Cache write failed:", e); }
  },

  get(key) {
    try {
      const item = JSON.parse(localStorage.getItem("tnx_" + key));
      if(!item) return null;
      if(Date.now() > item.expiry) {
        localStorage.removeItem("tnx_" + key);
        return null;
      }
      return item.data;
    } catch(e) { return null; }
  },

  clear(key) {
    localStorage.removeItem("tnx_" + key);
  },

  clearAll() {
    Object.keys(localStorage)
      .filter(k => k.startsWith("tnx_"))
      .forEach(k => localStorage.removeItem(k));
  }
};

// ═══════════════════════════════════════════════════════════════
// 🔁 5. RATE LIMIT CONTROLLER
// Prevent API overuse
// ═══════════════════════════════════════════════════════════════
const TNXRateLimit = {
  _lastCalls: {},
  _limits: {
    weather:    10 * 60 * 1000,  // 10 mins
    aqi:        15 * 60 * 1000,  // 15 mins
    earthquake: 5  * 60 * 1000,  // 5 mins
    forecast:   30 * 60 * 1000,  // 30 mins
    ui:         2  * 1000,       // 2 secs
  },

  canCall(source) {
    const now  = Date.now();
    const last = this._lastCalls[source] || 0;
    const limit = this._limits[source] || 5000;
    if(now - last < limit) return false;
    this._lastCalls[source] = now;
    return true;
  },

  reset(source) {
    this._lastCalls[source] = 0;
  }
};

// ═══════════════════════════════════════════════════════════════
// 📊 6. TIME-SERIES ENGINE
// Track historical values for charts
// ═══════════════════════════════════════════════════════════════
const TNXTimeSeries = {
  _series: {},
  _maxPoints: 24,

  push(key, value) {
    if(!this._series[key]) this._series[key] = [];
    this._series[key].push({
      value,
      timestamp: Date.now(),
      label: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    });
    if(this._series[key].length > this._maxPoints) {
      this._series[key].shift();
    }
    this._persist();
    TNXEvents.emit("timeSeriesUpdated", { key, series: this._series[key] });
  },

  get(key) {
    return this._series[key] || [];
  },

  getValues(key) {
    return (this._series[key] || []).map(p => p.value);
  },

  getLabels(key) {
    return (this._series[key] || []).map(p => p.label);
  },

  _persist() {
    TNXCache.set("timeseries", this._series, 24 * 60 * 60 * 1000); // 24hrs
  },

  load() {
    const saved = TNXCache.get("timeseries");
    if(saved) this._series = saved;
  }
};

// ═══════════════════════════════════════════════════════════════
// 🧪 7. VALIDATION LAYER
// Reject bad / anomalous data
// ═══════════════════════════════════════════════════════════════
const TNXValidator = {
  weather(data, prev) {
    if(!data || typeof data.temp !== "number") return { valid: false, reason: "Missing temperature" };
    if(data.temp < -80 || data.temp > 60)      return { valid: false, reason: `Temp out of range: ${data.temp}°C` };
    if(data.humidity < 0 || data.humidity > 100) return { valid: false, reason: "Invalid humidity" };
    if(prev && Math.abs(data.temp - prev.temp) > 15) {
      console.warn("TNX Anomaly: Temp spike detected", data.temp, "→", prev.temp);
      TNXEvents.emit("anomalyDetected", { type: "temp_spike", value: data.temp, prev: prev.temp });
    }
    return { valid: true };
  },

  aqi(data) {
    if(!data || typeof data.aqi !== "number") return { valid: false, reason: "Missing AQI" };
    if(data.aqi < 0 || data.aqi > 500)        return { valid: false, reason: "AQI out of range" };
    return { valid: true };
  },

  earthquake(data) {
    if(!data) return { valid: false, reason: "No earthquake data" };
    return { valid: true };
  }
};

// ═══════════════════════════════════════════════════════════════
// ⚙️ 8. NORMALIZATION LAYER
// Convert all API responses → same format
// ═══════════════════════════════════════════════════════════════
const TNXNormalizer = {
  weather(raw) {
    return {
      temp:        Math.round(raw.main.temp),
      feelsLike:   Math.round(raw.main.feels_like),
      humidity:    raw.main.humidity,
      wind:        raw.wind.speed,
      windDir:     raw.wind.deg || 0,
      visibility:  raw.visibility ? (raw.visibility / 1000).toFixed(1) : "--",
      description: raw.weather[0].description,
      main:        raw.weather[0].main,
      icon:        raw.weather[0].icon,
      sunrise:     new Date(raw.sys.sunrise * 1000),
      sunset:      new Date(raw.sys.sunset  * 1000),
      city:        raw.name,
      country:     raw.sys.country,
      pressure:    raw.main.pressure,
      clouds:      raw.clouds?.all || 0,
      source:      "OpenWeatherMap"
    };
  },

  aqi(raw) {
    const components = raw.list[0].components;
    const aqiIndex   = raw.list[0].main.aqi;
    const labels     = ["Good", "Fair", "Moderate", "Poor", "Very Poor"];
    return {
      aqi:       aqiIndex * 50,
      aqiIndex,
      label:     labels[aqiIndex - 1] || "Unknown",
      pm25:      components.pm2_5?.toFixed(1),
      pm10:      components.pm10?.toFixed(1),
      co:        components.co?.toFixed(1),
      no2:       components.no2?.toFixed(1),
      o3:        components.o3?.toFixed(1),
      source:    "OWM Air Pollution API"
    };
  },

  earthquake(raw) {
    const features = raw.features || [];
    if(features.length === 0) return { magnitude: 0, place: "None nearby", features: [] };
    const top = features[0];
    return {
      magnitude: top.properties.mag,
      place:     top.properties.place,
      time:      new Date(top.properties.time),
      depth:     top.geometry.coordinates[2],
      lat:       top.geometry.coordinates[1],
      lon:       top.geometry.coordinates[0],
      features,
      source:    "USGS"
    };
  }
};

// ═══════════════════════════════════════════════════════════════
// 🧮 9. DERIVED METRICS ENGINE
// Compute meaningful insights from raw data
// ═══════════════════════════════════════════════════════════════
const TNXMetrics = {
  heatIndex(temp, humidity) {
    if(temp < 27) return temp;
    const hi = -8.78469475556 +
      1.61139411 * temp +
      2.33854883889 * humidity +
      -0.14611605 * temp * humidity +
      -0.012308094 * temp * temp +
      -0.0164248277778 * humidity * humidity +
      0.002211732 * temp * temp * humidity +
      0.00072546 * temp * humidity * humidity +
      -0.000003582 * temp * temp * humidity * humidity;
    return Math.round(hi);
  },

  windChill(temp, windSpeed) {
    if(temp > 10 || windSpeed < 4.8) return temp;
    return Math.round(
      13.12 + 0.6215 * temp - 11.37 * Math.pow(windSpeed, 0.16) +
      0.3965 * temp * Math.pow(windSpeed, 0.16)
    );
  },

  uvRisk(clouds, hour) {
    const baseUV = hour >= 10 && hour <= 16 ? 8 : hour >= 7 && hour <= 19 ? 4 : 0;
    return Math.round(baseUV * (1 - clouds / 100));
  },

  riskScore(weather, aqi, earthquake) {
    let score = 0;
    if(weather) {
      if(weather.temp > 40)  score += 30;
      else if(weather.temp > 35) score += 20;
      else if(weather.temp > 30) score += 10;
      if(weather.wind > 15)  score += 20;
      else if(weather.wind > 10) score += 12;
      if(weather.main === "Thunderstorm") score += 15;
      if(weather.main === "Rain")         score += 8;
    }
    if(aqi) {
      if(aqi.aqi >= 200) score += 25;
      else if(aqi.aqi >= 150) score += 18;
      else if(aqi.aqi >= 100) score += 10;
    }
    if(earthquake && earthquake.magnitude >= 5) score += 20;
    else if(earthquake && earthquake.magnitude >= 3) score += 10;
    return Math.min(score, 100);
  },

  getDelta(newVal, oldVal) {
    if(oldVal === null || oldVal === undefined) return 0;
    return parseFloat((newVal - oldVal).toFixed(2));
  },

  getTrend(series) {
    if(!series || series.length < 2) return "stable";
    const last  = series[series.length - 1];
    const prev  = series[series.length - 2];
    const delta = last - prev;
    if(delta > 1)  return "rising";
    if(delta < -1) return "falling";
    return "stable";
  }
};

// ═══════════════════════════════════════════════════════════════
// 🧭 10. GEO GRID INDEXING
// Efficient region-based data lookup
// ═══════════════════════════════════════════════════════════════
const TNXGeoGrid = {
  getGrid(lat, lon) {
    return `${Math.floor(lat)}_${Math.floor(lon)}`;
  },

  getRegion(lat, lon) {
    if(lat >= 8  && lat <= 37  && lon >= 68 && lon <= 97)  return "South Asia";
    if(lat >= 35 && lat <= 70  && lon >= -10 && lon <= 40) return "Europe";
    if(lat >= -50 && lat <= -10 && lon >= 110 && lon <= 155) return "Australia";
    if(lat >= 15 && lat <= 55  && lon >= -130 && lon <= -60) return "North America";
    if(lat >= -55 && lat <= 15 && lon >= -85 && lon <= -30)  return "South America";
    if(lat >= -35 && lat <= 37  && lon >= -20 && lon <= 55)  return "Africa";
    return "Global";
  },

  getCountry(lat, lon) {
    if(lat >= 8  && lat <= 37  && lon >= 68 && lon <= 97)  return "IN";
    if(lat >= 24 && lat <= 50  && lon >= -125 && lon <= -66) return "US";
    if(lat >= 49 && lat <= 84  && lon >= -141 && lon <= -52) return "CA";
    if(lat >= -44 && lat <= -10 && lon >= 113 && lon <= 154) return "AU";
    if(lat >= 36 && lat <= 71  && lon >= -10 && lon <= 40)  return "EU";
    return "GLOBAL";
  }
};

// ═══════════════════════════════════════════════════════════════
// 📡 11. FETCH LAYER — Multi-source with failover
// ═══════════════════════════════════════════════════════════════
const TNXFetch = {
  OWM_KEY: "bd5e378503939ddaee76f12ad7a97608",

  async weather(lat, lon) {
    const cached = TNXCache.get(`weather_${lat}_${lon}`);
    if(cached) { TNXEvents.emit("log", "Weather loaded from cache"); return cached; }

    const t = Date.now();
    try {
      const res  = await fetch(`https://api.openweathermap.org/data/2.5/weather?lat=${lat}&lon=${lon}&appid=${this.OWM_KEY}&units=metric`);
      const raw  = await res.json();
      const data = TNXNormalizer.weather(raw);
      const validation = TNXValidator.weather(data, TNXState.get("weather"));
      if(!validation.valid) throw new Error(validation.reason);
      TNXCache.set(`weather_${lat}_${lon}`, data, 10 * 60 * 1000);
      TNXHealth.record("weather", "ok", Date.now() - t);
      return data;
    } catch(e) {
      TNXHealth.record("weather", "fail");
      TNXEvents.emit("log", `Weather fetch failed: ${e.message}`);
      return TNXCache.get(`weather_${lat}_${lon}`) || null;
    }
  },

  async aqi(lat, lon) {
    const cached = TNXCache.get(`aqi_${lat}_${lon}`);
    if(cached) return cached;

    const t = Date.now();
    try {
      const res  = await fetch(`https://api.openweathermap.org/data/2.5/air_pollution?lat=${lat}&lon=${lon}&appid=${this.OWM_KEY}`);
      const raw  = await res.json();
      const data = TNXNormalizer.aqi(raw);
      const validation = TNXValidator.aqi(data);
      if(!validation.valid) throw new Error(validation.reason);
      TNXCache.set(`aqi_${lat}_${lon}`, data, 15 * 60 * 1000);
      TNXHealth.record("aqi", "ok", Date.now() - t);
      return data;
    } catch(e) {
      TNXHealth.record("aqi", "fail");
      return null;
    }
  },

  async earthquake(lat, lon) {
    const cached = TNXCache.get(`eq_${lat}_${lon}`);
    if(cached) return cached;

    const t = Date.now();
    try {
      const res  = await fetch(`https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&latitude=${lat}&longitude=${lon}&maxradius=10&minmagnitude=2.0&orderby=time&limit=5`);
      const raw  = await res.json();
      const data = TNXNormalizer.earthquake(raw);
      TNXCache.set(`eq_${lat}_${lon}`, data, 5 * 60 * 1000);
      TNXHealth.record("earthquake", "ok", Date.now() - t);
      return data;
    } catch(e) {
      TNXHealth.record("earthquake", "fail");
      return null;
    }
  },

  async forecast(lat, lon) {
    const cached = TNXCache.get(`forecast_${lat}_${lon}`);
    if(cached) return cached;

    const t = Date.now();
    try {
      const res  = await fetch(`https://api.openweathermap.org/data/2.5/forecast?lat=${lat}&lon=${lon}&appid=${this.OWM_KEY}&units=metric`);
      const data = await res.json();
      TNXCache.set(`forecast_${lat}_${lon}`, data, 30 * 60 * 1000);
      TNXHealth.record("forecast", "ok", Date.now() - t);
      return data;
    } catch(e) {
      TNXHealth.record("forecast", "fail");
      return null;
    }
  }
};

// ═══════════════════════════════════════════════════════════════
// 🔍 12. QUERY SYSTEM — Internal API
// Clean access to all engine data
// ═══════════════════════════════════════════════════════════════
const TNXQuery = {
  get(type)         { return TNXState.get(type); },
  getWeather()      { return TNXState.get("weather"); },
  getAQI()          { return TNXState.get("aqi"); },
  getEarthquake()   { return TNXState.get("earthquake"); },
  getCity()         { return TNXState.get("city"); },
  getRiskScore()    { return TNXState.get("riskScore"); },
  getHistory(key)   { return TNXTimeSeries.get(key); },
  getHealth()       { return TNXHealth.getScore(); },
  isOnline()        { return TNXState.get("isOnline"); },
  getLastUpdated()  { return TNXState.get("lastUpdated"); }
};

// ═══════════════════════════════════════════════════════════════
// 🧩 13. PLUGGABLE MODULE SYSTEM
// Register/unregister data sources dynamically
// ═══════════════════════════════════════════════════════════════
const TNXModules = {
  _sources: {},

  register(name, fetchFn) {
    this._sources[name] = fetchFn;
    TNXEvents.emit("log", `Module registered: ${name}`);
  },

  unregister(name) {
    delete this._sources[name];
  },

  async run(name, ...args) {
    if(!this._sources[name]) return null;
    return await this._sources[name](...args);
  },

  list() {
    return Object.keys(this._sources);
  }
};

// Register default modules
TNXModules.register("weather",    (lat, lon) => TNXFetch.weather(lat, lon));
TNXModules.register("aqi",        (lat, lon) => TNXFetch.aqi(lat, lon));
TNXModules.register("earthquake", (lat, lon) => TNXFetch.earthquake(lat, lon));
TNXModules.register("forecast",   (lat, lon) => TNXFetch.forecast(lat, lon));

// ═══════════════════════════════════════════════════════════════
// 📦 14. OFFLINE SUPPORT
// Work without internet using cached data
// ═══════════════════════════════════════════════════════════════
const TNXOffline = {
  init() {
    window.addEventListener("online",  () => {
      TNXState.set("isOnline", true);
      TNXEvents.emit("onlineStatusChanged", { online: true });
      TNXEngine.sync(); // Re-sync when back online
    });
    window.addEventListener("offline", () => {
      TNXState.set("isOnline", false);
      TNXEvents.emit("onlineStatusChanged", { online: false });
    });
  }
};

// ═══════════════════════════════════════════════════════════════
// 🌟 15. UI LAYER — Smart DOM Updates
// ═══════════════════════════════════════════════════════════════
const TNXUI = {
  _icons: {
    "Clear":"☀️","Clouds":"☁️","Rain":"🌧️","Drizzle":"🌦️",
    "Thunderstorm":"⛈️","Snow":"❄️","Mist":"🌫️","Fog":"🌫️",
    "Haze":"🌫️","Dust":"🌪️","Tornado":"🌪️","Smoke":"🌫️"
  },

  icon(main) { return this._icons[main] || "🌡️"; },

  updateStatusBar(weather) {
    const el1 = document.getElementById("statusTemp");
    const el2 = document.getElementById("statusHumidity");
    if(el1 && weather) el1.innerText = `🌡 ${weather.city}: ${weather.temp}°C ${this.icon(weather.main)}`;
    if(el2 && weather) el2.innerText = `💧 Humidity: ${weather.humidity}%`;
  },

  updateDataCards(weather, aqi) {
    const cardAQI  = document.getElementById("cardAQI");
    const cardTemp = document.getElementById("cardTemp");
    const cardWind = document.getElementById("cardWind");

    if(cardTemp && weather) {
      const hi = TNXMetrics.heatIndex(weather.temp, weather.humidity);
      cardTemp.innerText = `${weather.temp}°C — ${weather.main} (Feels ${hi}°C)`;
    }
    if(cardWind && weather) {
      const trend = TNXMetrics.getTrend(TNXTimeSeries.getValues("wind"));
      const arrow = trend === "rising" ? "↑" : trend === "falling" ? "↓" : "→";
      cardWind.innerText = `${weather.wind} m/s ${arrow}`;
    }
    if(cardAQI && aqi) {
      cardAQI.innerText = `${aqi.label} (${aqi.aqi} AQI)`;
    }
  },

  showGreeting(user, weather) {
    const hour = new Date().getHours();
    const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
    const name  = user?.displayName?.split(" ")[0] || "Explorer";
    const city  = weather?.city || "";
    const temp  = weather?.temp || "--";
    const desc  = weather?.description || "";

    let existing = document.getElementById("tnx-greeting");
    if(!existing) {
      existing = document.createElement("div");
      existing.id = "tnx-greeting";
      existing.style.cssText = `
        position:fixed;top:75px;left:50%;transform:translateX(-50%);
        background:rgba(10,10,10,0.92);backdrop-filter:blur(20px);
        border:1px solid rgba(31,111,67,0.4);border-radius:12px;
        padding:12px 24px;color:#d2d8d2;font-size:13px;
        z-index:998;font-family:'Inter',sans-serif;
        animation:tnxSlideDown 0.4s ease;
        box-shadow:0 8px 32px rgba(0,0,0,0.4);
        white-space:nowrap;
      `;
      document.head.insertAdjacentHTML("beforeend", `
        <style>
          @keyframes tnxSlideDown{from{opacity:0;transform:translateX(-50%) translateY(-10px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}
          @keyframes tnxFadeOut{from{opacity:1}to{opacity:0;transform:translateX(-50%) translateY(-10px)}}
        </style>
      `);
      document.body.appendChild(existing);
      setTimeout(() => {
        existing.style.animation = "tnxFadeOut 0.4s ease forwards";
        setTimeout(() => existing.remove(), 400);
      }, 5000);
    }
    existing.innerHTML = `
      <span style="color:#1f6f43;">👋 ${greeting}, ${name}!</span>
      ${city ? `<span style="color:#555;margin:0 8px;">•</span><span>📍 ${city}: ${temp}°C, ${desc}</span>` : ""}
    `;
  },

  showToast(message, type = "info", duration = 4000) {
    const colors = {
      info:    { bg: "rgba(31,111,67,0.15)",  border: "#1f6f43", text: "#4caf50" },
      warning: { bg: "rgba(138,109,59,0.15)", border: "#8a6d3b", text: "#d2b48c" },
      danger:  { bg: "rgba(122,31,43,0.2)",   border: "#7a1f2b", text: "#ff6b6b" },
      alert:   { bg: "rgba(255,77,77,0.15)",  border: "#ff4d4d", text: "#ff4d4d" },
    };
    const c = colors[type] || colors.info;

    let container = document.getElementById("tnx-toasts");
    if(!container) {
      container = document.createElement("div");
      container.id = "tnx-toasts";
      container.style.cssText = `
        position:fixed;bottom:24px;right:24px;
        display:flex;flex-direction:column;gap:10px;
        z-index:9999;max-width:340px;
      `;
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.style.cssText = `
      background:${c.bg};border:1px solid ${c.border};
      border-radius:10px;padding:12px 16px;
      color:${c.text};font-size:13px;font-family:'Inter',sans-serif;
      backdrop-filter:blur(10px);
      animation:tnxToastIn 0.3s ease;
      box-shadow:0 4px 20px rgba(0,0,0,0.3);
      cursor:pointer;line-height:1.5;
    `;
    document.head.insertAdjacentHTML("beforeend", `
      <style>
        @keyframes tnxToastIn{from{opacity:0;transform:translateX(20px)}to{opacity:1;transform:translateX(0)}}
        @keyframes tnxToastOut{from{opacity:1}to{opacity:0;transform:translateX(20px)}}
      </style>
    `);
    toast.innerHTML = message;
    toast.onclick = () => toast.remove();
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.animation = "tnxToastOut 0.3s ease forwards";
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  showDisasterAlert(earthquake) {
    if(!earthquake || earthquake.magnitude < 3) return;
    const level = earthquake.magnitude >= 6 ? "danger" : earthquake.magnitude >= 4 ? "warning" : "info";
    this.showToast(
      `🌍 <strong>Earthquake Detected!</strong><br>M${earthquake.magnitude.toFixed(1)} — ${earthquake.place}`,
      level, 8000
    );
  },

  showWeatherAlert(weather) {
    if(!weather) return;
    if(weather.main === "Thunderstorm") {
      this.showToast(`⛈️ <strong>Thunderstorm Alert</strong><br>Active in ${weather.city}. Stay indoors!`, "danger", 6000);
    } else if(weather.temp > 40) {
      this.showToast(`🔥 <strong>Extreme Heat Warning</strong><br>${weather.temp}°C in ${weather.city}. Stay hydrated!`, "alert", 6000);
    } else if(weather.temp > 35) {
      this.showToast(`☀️ <strong>Heat Advisory</strong><br>${weather.temp}°C in ${weather.city}. Limit sun exposure.`, "warning", 5000);
    }
    if(weather.wind > 15) {
      this.showToast(`💨 <strong>Strong Wind Alert</strong><br>${weather.wind} m/s in ${weather.city}. Secure loose items.`, "warning", 5000);
    }
  },

  updateOnlineStatus(online) {
    if(!online) {
      this.showToast("📡 <strong>Offline Mode</strong><br>Showing cached data. Reconnecting...", "warning", 0);
    } else {
      this.showToast("✅ <strong>Back Online</strong><br>Syncing latest data...", "info", 3000);
    }
  }
};

// ═══════════════════════════════════════════════════════════════
// 🔄 16. BACKGROUND SYNC ENGINE
// Continuous updates with smart scheduling
// ═══════════════════════════════════════════════════════════════
const TNXSync = {
  _intervals: [],

  start(lat, lon) {
    this.stop(); // Clear existing

    // Fast sync — weather every 10 mins
    this._intervals.push(setInterval(async () => {
      if(!TNXState.get("isOnline")) return;
      await TNXEngine.syncWeather(lat, lon);
    }, 10 * 60 * 1000));

    // Medium sync — AQI every 15 mins
    this._intervals.push(setInterval(async () => {
      if(!TNXState.get("isOnline")) return;
      await TNXEngine.syncAQI(lat, lon);
    }, 15 * 60 * 1000));

    // Slow sync — earthquakes every 5 mins
    this._intervals.push(setInterval(async () => {
      if(!TNXState.get("isOnline")) return;
      await TNXEngine.syncEarthquake(lat, lon);
    }, 5 * 60 * 1000));

    TNXEvents.emit("log", "Background sync started");
  },

  stop() {
    this._intervals.forEach(id => clearInterval(id));
    this._intervals = [];
  }
};

// ═══════════════════════════════════════════════════════════════
// 🚀 17. MAIN ENGINE — Orchestrator
// ═══════════════════════════════════════════════════════════════
const TNXEngine = {
  async init(lat, lon, user = null) {
    TNXTimeSeries.load();
    TNXOffline.init();

    TNXState.set("lat", lat);
    TNXState.set("lon", lon);
    TNXState.set("user", user);

    await this.sync();
    TNXSync.start(lat, lon);
    TNXEvents.emit("engineReady", { lat, lon });
    TNXEvents.emit("log", `TNX Engine initialized at [${lat}, ${lon}]`);
  },

  async sync() {
    const lat = TNXState.get("lat");
    const lon = TNXState.get("lon");
    if(!lat || !lon) return;

    await Promise.all([
      this.syncWeather(lat, lon),
      this.syncAQI(lat, lon),
      this.syncEarthquake(lat, lon),
    ]);

    TNXState.set("lastUpdated", new Date().toLocaleTimeString());
    TNXEvents.emit("syncComplete", { timestamp: Date.now() });
  },

  async syncWeather(lat, lon) {
    const data = await TNXFetch.weather(lat, lon);
    if(!data) return;

    const prev = TNXState.get("weather");
    TNXState.set("weather", data);
    TNXState.set("city", data.city);

    TNXTimeSeries.push("temp",     data.temp);
    TNXTimeSeries.push("humidity", data.humidity);
    TNXTimeSeries.push("wind",     data.wind);

    this._updateRiskScore();
    TNXUI.updateStatusBar(data);
    TNXUI.updateDataCards(data, TNXState.get("aqi"));
    TNXUI.showGreeting(TNXState.get("user"), data);
    TNXUI.showWeatherAlert(data);

    TNXEvents.emit("weatherUpdated", data);
  },

  async syncAQI(lat, lon) {
    const data = await TNXFetch.aqi(lat, lon);
    if(!data) return;

    TNXState.set("aqi", data);
    TNXTimeSeries.push("aqi", data.aqi);
    this._updateRiskScore();
    TNXUI.updateDataCards(TNXState.get("weather"), data);

    TNXEvents.emit("aqiUpdated", data);
  },

  async syncEarthquake(lat, lon) {
    const data = await TNXFetch.earthquake(lat, lon);
    if(!data) return;

    const prev = TNXState.get("earthquake");
    TNXState.set("earthquake", data);

    // Alert only for new earthquakes
    if(data.magnitude > 0 && (!prev || data.time > prev?.time)) {
      TNXUI.showDisasterAlert(data);
    }

    this._updateRiskScore();
    TNXEvents.emit("earthquakeUpdated", data);
  },

  _updateRiskScore() {
    const score = TNXMetrics.riskScore(
      TNXState.get("weather"),
      TNXState.get("aqi"),
      TNXState.get("earthquake")
    );
    TNXState.set("riskScore", score);
    TNXEvents.emit("riskScoreUpdated", { score });
  }
};

// ═══════════════════════════════════════════════════════════════
// 📍 18. LOCATION RESOLVER
// Firestore city → GPS → Chennai fallback
// ═══════════════════════════════════════════════════════════════
const TNXLocation = {
  async resolve(firestoreCity = null) {
    // Priority 1: Firestore saved city
    if(firestoreCity) {
      try {
        const OWM_KEY = "bd5e378503939ddaee76f12ad7a97608";
        const res  = await fetch(`https://api.openweathermap.org/data/2.5/weather?q=${encodeURIComponent(firestoreCity)}&appid=${OWM_KEY}&units=metric`);
        const data = await res.json();
        if(data.cod === 200) {
          TNXEvents.emit("log", `Location resolved from Firestore: ${firestoreCity}`);
          return { lat: data.coord.lat, lon: data.coord.lon, source: "firestore" };
        }
      } catch(e) {}
    }

    // Priority 2: Browser GPS
    return new Promise(resolve => {
      if(navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          pos => {
            TNXEvents.emit("log", "Location resolved from GPS");
            resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude, source: "gps" });
          },
          () => {
            TNXEvents.emit("log", "GPS denied — using Chennai fallback");
            resolve({ lat: 13.0827, lon: 80.2707, source: "fallback" });
          },
          { timeout: 5000 }
        );
      } else {
        resolve({ lat: 13.0827, lon: 80.2707, source: "fallback" });
      }
    });
  }
};

// ═══════════════════════════════════════════════════════════════
// 📝 19. ENGINE LOGGER
// Dev-friendly logging system
// ═══════════════════════════════════════════════════════════════
TNXEvents.on("log", (msg) => {
  console.log(`%c[TNX Engine] ${msg}`, "color:#1f6f43;font-weight:600;");
});

TNXEvents.on("anomalyDetected", (data) => {
  console.warn(`%c[TNX Anomaly] ${JSON.stringify(data)}`, "color:#ff9800;font-weight:600;");
  TNXUI.showToast(`⚠️ <strong>Data Anomaly Detected</strong><br>${data.type}: ${data.value}`, "warning", 4000);
});

TNXEvents.on("onlineStatusChanged", ({ online }) => {
  TNXUI.updateOnlineStatus(online);
});

// ═══════════════════════════════════════════════════════════════
// 🌐 GLOBAL EXPORT
// ═══════════════════════════════════════════════════════════════
window.TNX = {
  Engine:     TNXEngine,
  State:      TNXState,
  Events:     TNXEvents,
  Query:      TNXQuery,
  UI:         TNXUI,
  Cache:      TNXCache,
  Metrics:    TNXMetrics,
  TimeSeries: TNXTimeSeries,
  Health:     TNXHealth,
  Location:   TNXLocation,
  Modules:    TNXModules,
  GeoGrid:    TNXGeoGrid,
};

console.log("%c🌍 TerranovaX Engine v1.0 Loaded", "color:#1f6f43;font-size:14px;font-weight:700;");
console.log("%c19-System Architecture Ready", "color:#8a6d3b;font-size:12px;");