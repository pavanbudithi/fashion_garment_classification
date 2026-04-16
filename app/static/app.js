const uploadForm = document.getElementById("uploadForm");
const uploadStatus = document.getElementById("uploadStatus");
const refreshBtn = document.getElementById("refreshBtn");

const searchInput = document.getElementById("searchInput");
const garmentTypeFilter = document.getElementById("garmentTypeFilter");
const styleFilter = document.getElementById("styleFilter");
const materialFilter = document.getElementById("materialFilter");
const occasionFilter = document.getElementById("occasionFilter");
const seasonFilter = document.getElementById("seasonFilter");
const countryFilter = document.getElementById("countryFilter");
const designerFilter = document.getElementById("designerFilter");

const applyFiltersBtn = document.getElementById("applyFiltersBtn");
const clearFiltersBtn = document.getElementById("clearFiltersBtn");

const gallery = document.getElementById("gallery");
const emptyState = document.getElementById("emptyState");
const resultsMeta = document.getElementById("resultsMeta");

document.addEventListener("DOMContentLoaded", async () => {
  await loadFilters();
  await loadGarments();
});

refreshBtn.addEventListener("click", async () => {
  await loadFilters();
  await loadGarments();
});

applyFiltersBtn.addEventListener("click", loadGarments);

clearFiltersBtn.addEventListener("click", async () => {
  searchInput.value = "";
  garmentTypeFilter.value = "";
  styleFilter.value = "";
  materialFilter.value = "";
  occasionFilter.value = "";
  seasonFilter.value = "";
  countryFilter.value = "";
  designerFilter.value = "";
  await loadGarments();
});

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  uploadStatus.textContent = "Uploading and classifying...";

  const formData = new FormData(uploadForm);

  try {
    const response = await fetch("/upload", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Upload failed");
    }

    uploadStatus.textContent = "Upload completed successfully.";
    uploadForm.reset();
    await loadFilters();
    await loadGarments();
  } catch (err) {
    uploadStatus.textContent = err.message || "Upload failed.";
  }
});

async function loadFilters() {
  try {
    const response = await fetch("/garments/filters/");
    const data = await response.json();

    fillSelect(garmentTypeFilter, data.garment_attributes?.garment_types || []);
    fillSelect(styleFilter, data.garment_attributes?.styles || []);
    fillSelect(materialFilter, data.garment_attributes?.materials || []);
    fillSelect(occasionFilter, data.garment_attributes?.occasions || []);
    fillSelect(designerFilter, data.garment_attributes?.designers || []);
    fillSelect(seasonFilter, data.context?.seasons || []);
    fillSelect(countryFilter, data.context?.countries || []);
  } catch (err) {
    console.error("Failed to load filters", err);
  }
}

function fillSelect(selectEl, values) {
  const currentValue = selectEl.value;
  const firstOption = selectEl.querySelector("option")?.outerHTML || `<option value="">All</option>`;
  selectEl.innerHTML = firstOption;

  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    selectEl.appendChild(option);
  });

  if ([...selectEl.options].some((o) => o.value === currentValue)) {
    selectEl.value = currentValue;
  }
}

async function loadGarments() {
  resultsMeta.textContent = "Loading...";
  gallery.innerHTML = "";
  emptyState.classList.add("hidden");

  const params = new URLSearchParams();

  if (searchInput.value.trim()) params.set("q", searchInput.value.trim());
  if (garmentTypeFilter.value) params.set("garment_type", garmentTypeFilter.value);
  if (styleFilter.value) params.set("style", styleFilter.value);
  if (materialFilter.value) params.set("material", materialFilter.value);
  if (occasionFilter.value) params.set("occasion", occasionFilter.value);
  if (seasonFilter.value) params.set("season", seasonFilter.value);
  if (countryFilter.value) params.set("country", countryFilter.value);
  if (designerFilter.value) params.set("designer", designerFilter.value);

  try {
    const response = await fetch(`/garments/search?${params.toString()}`);
    const data = await response.json();

    const results = data.results || [];
    resultsMeta.textContent = `${data.total || 0} result(s)`;

    if (!results.length) {
      emptyState.classList.remove("hidden");
      return;
    }

    results.forEach((item) => {
      gallery.appendChild(renderCard(item));
    });
  } catch (err) {
    console.error("Failed to load garments", err);
    resultsMeta.textContent = "Failed to load results";
  }
}

function renderCard(item) {
  const card = document.createElement("article");
  card.className = "card";

  const imageUrl = resolveImageUrl(item.stored_path);

  card.innerHTML = `
    <div class="card-image-wrap">
      <img class="card-image" src="${imageUrl}" alt="${escapeHtml(item.original_filename || "uploaded garment")}" />
    </div>

    <div class="card-body">
      <h3>${escapeHtml(item.garment_type || "Unknown garment")}</h3>
      <p class="description">${escapeHtml(item.description || "No description available.")}</p>

      <div class="meta-grid">
        ${metaRow("Style", item.style)}
        ${metaRow("Material", item.material)}
        ${metaRow("Occasion", item.occasion)}
        ${metaRow("Pattern", item.pattern)}
        ${metaRow("Season", item.time_season || item.season)}
        ${metaRow("Country", item.location_country)}
        ${metaRow("Designer", item.designer)}
      </div>
    </div>
  `;

  return card;
}

function metaRow(label, value) {
  return `
    <div class="meta-item">
      <span class="meta-label">${escapeHtml(label)}</span>
      <span class="meta-value">${escapeHtml(value || "—")}</span>
    </div>
  `;
}

function resolveImageUrl(storedPath) {
  if (!storedPath) return "";
  const normalized = String(storedPath).replaceAll("\\", "/");

  if (normalized.startsWith("http://") || normalized.startsWith("https://")) {
    return normalized;
  }

  const uploadsIdx = normalized.toLowerCase().lastIndexOf("uploads/");
  if (uploadsIdx !== -1) {
    return "/" + normalized.slice(uploadsIdx);
  }

  const fileName = normalized.split("/").pop();
  return `/uploads/${encodeURIComponent(fileName)}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}