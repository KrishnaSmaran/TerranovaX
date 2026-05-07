// SCENE
const scene = new THREE.Scene();

// CAMERA
const camera = new THREE.PerspectiveCamera(55, window.innerWidth/window.innerHeight, 0.1, 2000);
camera.position.z = window.innerWidth < 768 ? 3.8 : 3;

// RENDERER
const renderer = new THREE.WebGLRenderer({antialias:true, alpha:true});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
document.getElementById("earth-container").appendChild(renderer.domElement);

// LIGHT (SUN)
const sunLight = new THREE.DirectionalLight(0xffffff, 0.5);
sunLight.position.set(5,3,5);
scene.add(sunLight);

// AMBIENT
scene.add(new THREE.AmbientLight(0x404040, 1));

// TEXTURE LOADER
const loader = new THREE.TextureLoader();

// 🌍 EARTH
const geometry = new THREE.SphereGeometry(1.3, 128, 128);

const material = new THREE.MeshPhongMaterial({
  map: loader.load("https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_atmos_2048.jpg")
});

const earth = new THREE.Mesh(geometry, material);
scene.add(earth);




// 🌃 NIGHT LIGHTS (FIXED)
const nightMaterial = new THREE.MeshBasicMaterial({
  map: loader.load("https://threejsfundamentals.org/threejs/resources/images/earth-night.jpg"),
  blending: THREE.AdditiveBlending,
  transparent:true,
  opacity:0.25 // FIXED
});

// slightly bigger than earth (IMPORTANT)
const nightMesh = new THREE.Mesh(
  new THREE.SphereGeometry(1.301, 128, 128),
  nightMaterial
);

scene.add(nightMesh);

// ☁ CLOUDS
const cloudGeo = new THREE.SphereGeometry(1.32, 128, 128);

const cloudMat = new THREE.MeshPhongMaterial({
  map: loader.load("https://raw.githubusercontent.com/jeromeetienne/threex.planets/master/images/earthmap1k.jpg"),
  transparent:true,
  opacity:1
});

const clouds = new THREE.Mesh(cloudGeo, cloudMat);
scene.add(clouds);

// 🌫 ATMOSPHERE
const atmosphereGeo = new THREE.SphereGeometry(1.38, 128, 128);

const atmosphereMat = new THREE.MeshBasicMaterial({
  color: 0x2ecc71,
  transparent: true,
  opacity: 0.05,
  side: THREE.BackSide
});

const atmosphere = new THREE.Mesh(atmosphereGeo, atmosphereMat);
scene.add(atmosphere);

// ✨ STARS
const starGeo = new THREE.BufferGeometry();
const starVertices = [];

for(let i=0;i<20000;i++){
  starVertices.push(
    (Math.random()-0.5)*3000,
    (Math.random()-0.5)*3000,
    (Math.random()-0.5)*3000
  );
}

starGeo.setAttribute('position', new THREE.Float32BufferAttribute(starVertices,3));

const starMat = new THREE.PointsMaterial({
  color:0xffffff,
  size:0.7
});

const stars = new THREE.Points(starGeo, starMat);
scene.add(stars);



// 🌍 EXTRA LAND VISIBILITY BOOST (SAFE ADD)
earth.material.emissive = new THREE.Color(0x112244);
earth.material.emissiveIntensity = 0.25;



// 🛰 REAL NASA ISS
let iss;

const gltfLoader = new THREE.GLTFLoader();

const dracoLoader = new THREE.DRACOLoader();
dracoLoader.setDecoderPath("https://www.gstatic.com/draco/v1/decoders/");
dracoLoader.setDecoderPath("https://www.gstatic.com/draco/v1/decoders/");
gltfLoader.setDRACOLoader(dracoLoader);

gltfLoader.load("/static/models/iss.glb", function(gltf) {
  iss = gltf.scene;

  // 🔥 CRITICAL SCALE FIX (NASA model is HUGE)
  iss.scale.set(0.15, 0.15, 0.15);
  iss.position.set(2.5, 0.5, 0);

  scene.add(iss);
});


// ANIMATION
let angle = 0;

function animate(){
  requestAnimationFrame(animate);
  angle += 0.01;

  // earth rotation
  earth.rotation.y += 0.0015;

  // 🔥 FIX: sync lights with earth
  nightMesh.rotation.y = earth.rotation.y;

  clouds.rotation.y += 0.002;


  // ISS-style tilted orbit
  if (iss) {

  const radius = 2.8;
  const tilt = 0.3;
  const angle = Date.now() * 0.0002;

  iss.position.set(
    Math.cos(angle) * radius,
    Math.sin(angle * tilt),
    Math.sin(angle) * radius
  );

  // face Earth
  iss.lookAt(0, 0, 0);

  // slight self rotation
  iss.rotation.y += 0.002;
}
  renderer.render(scene, camera);
}

animate();

// RESIZE
window.addEventListener("resize", () => {
  const container = document.getElementById("earth-container");

  const width = container.clientWidth;
  const height = container.clientHeight;

  renderer.setSize(width, height);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
});

document.addEventListener("DOMContentLoaded", () => {
  const stars = document.querySelectorAll(".interactive-review .star");
  const feedbackBox = document.getElementById("feedbackBox");

  // Create Thank You card element
  const thankYouCard = document.createElement("div");
  thankYouCard.className = "thank-you-card";
  thankYouCard.innerHTML = "<p>Thank you for your feedback!</p>";
  thankYouCard.style.display = "none";
  document.querySelector(".interactive-review").appendChild(thankYouCard);

  let selectedRating = 0;

  stars.forEach(star => {
    star.addEventListener("mouseover", () => highlightStars(star.dataset.value));
    star.addEventListener("mouseout", resetStars);
    star.addEventListener("click", () => {
      selectStars(star.dataset.value);
      feedbackBox.style.display = "block";
      feedbackBox.scrollIntoView({behavior: "smooth"});
    });
  });

  function highlightStars(value){
    stars.forEach(s => s.classList.toggle("hover", s.dataset.value <= value));
  }

  function resetStars(){
    stars.forEach(s => s.classList.remove("hover"));
  }

  function selectStars(value){
    selectedRating = value;
    stars.forEach(s => s.classList.toggle("selected", s.dataset.value <= value));
  }

  // Handle feedback submit
  const submitBtn = feedbackBox.querySelector("button");
  submitBtn.addEventListener("click", (e) => {
    e.preventDefault();

    // hide feedback box
    feedbackBox.style.display = "none";

    // show thank you card
    thankYouCard.style.display = "flex";

    // after 2 seconds, hide thank you and reset stars
    setTimeout(() => {
      thankYouCard.style.display = "none";
      stars.forEach(s => s.classList.remove("selected"));
      selectedRating = 0;
      feedbackBox.style.display = "none";
      stars.forEach(s => s.classList.remove("hover"));
      window.scrollTo({top: document.querySelector(".interactive-review").offsetTop, behavior:"smooth"});
    }, 2000);
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const btnReport = document.querySelector(".btn-report");
  const reportForm = document.getElementById("reportForm");
  const submitReport = document.getElementById("submitReport");
  const thankYouReport = document.getElementById("thankYouReport");

  // Show form when Report Now clicked
  btnReport.addEventListener("click", () => {
    reportForm.style.display = "flex";
    reportForm.scrollIntoView({behavior: "smooth"});
  });

  // Handle form submission
  submitReport.addEventListener("click", (e) => {
    e.preventDefault();

    const name = document.getElementById("reportName").value.trim();
    const from = document.getElementById("reportFrom").value.trim();
    const what = document.getElementById("reportWhat").value.trim();

    if(!name || !from || !what){
      alert("Please fill all fields!");
      return;
    }

    // Send data to your Gmail via EmailJS (or backend API)
    // Example: EmailJS usage here (you can configure)
    /*
    emailjs.send("service_id","template_id",{
      from_name:name,
      from_location:from,
      message:what
    });
    */

    // Hide form, show thank you
    reportForm.style.display = "none";
    thankYouReport.style.display = "flex";

    setTimeout(() => {
      thankYouReport.style.display = "none";
      reportForm.style.display = "none";
      document.getElementById("reportName").value = "";
      document.getElementById("reportFrom").value = "";
      document.getElementById("reportWhat").value = "";
      window.scrollTo({top: btnReport.offsetTop - 100, behavior: "smooth"});
    }, 2000);
  });
});
let keys = "";
document.addEventListener("keydown",(e)=>{
  keys += e.key.toLowerCase();
  if(keys.includes("nova")){
    document.body.style.filter = "hue-rotate(120deg)";
    keys="";
  }
});
// ════════════════════════════════════════════════════════════════
// STEP 2 — Add this to your main.js (paste at the very bottom)
// ════════════════════════════════════════════════════════════════

// ── SUBSCRIBE SECTION LOGIC ──
(function() {

  function checkSubscribed() {
    return localStorage.getItem("tx_subscribed") === "true";
  }

  function showSubscribedState() {
    const sv = document.getElementById("subscribeView");
    const dv = document.getElementById("subscribedView");
    if (sv) sv.style.display = "none";
    if (dv) dv.style.display = "block";
  }

  // On page load — check if already subscribed
  window.addEventListener("DOMContentLoaded", function() {
    if (checkSubscribed()) {
      showSubscribedState();
    }

    // Scroll to #subscribe if URL has #subscribe
    if (window.location.hash === "#subscribe") {
      const el = document.getElementById("subscribe");
      if (el) el.scrollIntoView({ behavior: "smooth" });
    }
  });

  // Handle subscribe form submit
  window.handleSubscribe = async function(e) {
    e.preventDefault();

    const emailInput = document.getElementById("subscribeEmail");
    const btn        = document.getElementById("subscribeBtnText");
    const msg        = document.getElementById("subscribeMsg");

    const email = emailInput.value.trim();
    if (!email) return;

    btn.textContent = "Subscribing…";
    btn.disabled = true;

    try {
      const res = await fetch("/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email })
      });

      const data = await res.json();

      if (res.ok || res.status === 409) {
        // Mark subscribed in localStorage
        localStorage.setItem("tx_subscribed", "true");
        localStorage.setItem("tx_email", email);

        // Smooth transition
        msg.style.display = "block";
        msg.textContent = "✅ Subscribed! Welcome to TerranovaX.";

        setTimeout(() => {
          showSubscribedState();
        }, 1200);
      } else {
        btn.textContent = "Subscribe";
        btn.disabled = false;
        msg.style.display = "block";
        msg.style.color = "#ff6b6b";
        msg.textContent = data.error || "Something went wrong. Please try again.";
      }
    } catch(err) {
      // Network error — still allow (localStorage only)
      localStorage.setItem("tx_subscribed", "true");
      localStorage.setItem("tx_email", email);
      setTimeout(() => showSubscribedState(), 800);
    }
  };

})();

