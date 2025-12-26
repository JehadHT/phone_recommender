let priceSlider;
let currentPhones = [];

// ----------------------
// Load price range
// ----------------------
async function loadPriceRange() {
    const sliderElement = document.getElementById("price-slider");
    if (!sliderElement) return;

    // Prevent double-initialization (this can break noUiSlider)
    if (sliderElement.noUiSlider) {
        priceSlider = sliderElement.noUiSlider;
        return;
    }

    const res = await fetch("http://127.0.0.1:8000/price-range");
    const data = await res.json();

    priceSlider = noUiSlider.create(sliderElement, {
        start: [data.min, data.max],
        connect: true,
        step: 1,
        range: {
            min: data.min,
            max: data.max
        },
        tooltips: [
            { to: v => `$ ${Math.round(v)}` },
            { to: v => `$ ${Math.round(v)}` }
        ]
    });

    priceSlider.on("update", values => {
        const label = document.getElementById("price-value");
        if (label) {
            label.textContent =
                `$ ${Math.round(values[0])} - $ ${Math.round(values[1])}`;
        }
    });
}

// ----------------------
// Load brands
// ----------------------
async function loadBrands() {
    const select = document.getElementById("brand");
    if (!select) return;

    const res = await fetch("http://127.0.0.1:8000/brands");
    const brands = await res.json();

    brands.forEach(brand => {
        const option = document.createElement("option");
        option.value = brand;
        option.textContent = brand;
        select.appendChild(option);
    });
}

// ----------------------
// Helpers
// ----------------------
function getNumber(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    return el.value === "" ? null : Number(el.value);
}

// ----------------------
// Search phones
// ----------------------
async function searchPhones() {
    if (!priceSlider) return;

    const [minPrice, maxPrice] = priceSlider.get().map(Number);

    const data = {
        brand: document.getElementById("brand")?.value || null,
        min_price: minPrice,
        max_price: maxPrice,
        min_battery: getNumber("min_battery"),
        min_ram: getNumber("min_ram"),
        min_camera_mp: getNumber("min_camera")
    };

    console.log("📤 Sending request:", data);

    const response = await fetch("http://127.0.0.1:8000/filter", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });

    const result = await response.json();
    console.log("📥 Response:", result.results);

    localStorage.setItem("lastSearchFilters", JSON.stringify(data));
    localStorage.setItem("lastSearchResults", JSON.stringify(result.results));

    currentPhones = result.results;
    renderResults(currentPhones);
}

// ----------------------
// Render results
// ----------------------
function renderResults(phones) {
    const container = document.getElementById("results");
    if (!container) return;

    container.innerHTML = "";

    if (phones.length === 0) {
        container.innerHTML = "<p>No phones found ❌</p>";
        return;
    }

    phones.forEach((phone, index) => {
        const div = document.createElement("div");
        div.className = "phone";
        div.style.display = "flex";
        div.style.gap = "15px";
        div.style.alignItems = "center";

        // -------------------
        // Image thumbnail
        // -------------------
        let imageHTML = `
            <div style="width:120px;height:120px;display:flex;align-items:center;justify-content:center;
                        background:#f1f1f1;border-radius:8px;font-size:14px;color:#888;">
                No Image
            </div>
        `;

        if (phone.image_url) {
            if (
                phone.image_url.endsWith(".jpg") ||
                phone.image_url.endsWith(".png") ||
                phone.image_url.endsWith(".webp")
            ) {
                imageHTML = `
                    <img src="${phone.image_url}"
                         style="width:120px;height:120px;object-fit:cover;border-radius:8px;"
                         alt="Phone image"
                         onerror="this.style.display='none'">
                `;
            } else if (phone.image_url.includes("sketchfab.com")) {
                imageHTML = `
                    <div style="width:120px;height:120px;
                                display:flex;align-items:center;justify-content:center;
                                background:#000;border-radius:8px;color:#fff;font-size:14px;">
                        3D Model
                    </div>
                `;
            }
        }

        // -------------------
        // Phone info
        // -------------------
        div.innerHTML = `
            ${imageHTML}
            <div style="flex:1;">
                <h3>${phone.name}</h3>
                <p><strong>${phone.brand}</strong></p>
                <p>💰 Price: $${phone.price}</p>
                <p>🔋 Battery: ${phone.battery} mAh</p>
                <p>📷 Camera: ${phone.camera_mp} MP</p>
                <p>🧠 RAM: ${phone.ram} MB</p>
                <p>⭐ Match Score: ${phone.match_percentage}%</p>
                <button class="details-btn" data-index="${index}">
                    📸 View Details
                </button>
            </div>
        `;

        container.appendChild(div);
    });

    // ربط الأزرار
    document.querySelectorAll(".details-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const phone = phones[btn.dataset.index];
            localStorage.setItem("selectedPhone", JSON.stringify(phone));
            window.location.href = "phone-details.html";
        });
    });
}


// ----------------------
// Init (Safe for all pages)
// ----------------------
document.addEventListener("DOMContentLoaded", () => {
    // Always start with default values on refresh
    localStorage.removeItem("lastSearchFilters");
    localStorage.removeItem("lastSearchResults");

    const hasSlider = !!document.getElementById("price-slider");
    const hasBrand = !!document.getElementById("brand");

    if (hasBrand) {
        loadBrands();
    }

    if (hasSlider) {
        loadPriceRange().then(() => {
            restoreLastSearch();
        });
    }
});

function restoreLastSearch() {
    const filters = localStorage.getItem("lastSearchFilters");
    const results = localStorage.getItem("lastSearchResults");

    if (!filters || !results) return;

    const f = JSON.parse(filters);
    const phones = JSON.parse(results);

    // استرجاع القيم
    const brandEl = document.getElementById("brand");
    if (brandEl) brandEl.value = f.brand || "";

    const minBatteryEl = document.getElementById("min_battery");
    if (minBatteryEl) minBatteryEl.value = f.min_battery || "";

    const minRamEl = document.getElementById("min_ram");
    if (minRamEl) minRamEl.value = f.min_ram || "";

    const minCameraEl = document.getElementById("min_camera");
    if (minCameraEl) minCameraEl.value = f.min_camera_mp || "";

    // استرجاع السلايدر (بعد تحميله)
    if (priceSlider) {
        priceSlider.set([f.min_price, f.max_price]);
    }

    // عرض النتائج
    renderResults(phones);
}
