// ===== GLOBAL =====
window.currentItemId = window.currentItemId || null;

document.addEventListener("DOMContentLoaded", () => {
  console.log("DOM READY");

  // ===== DARK MODE TOGGLE =====
  const btn = document.getElementById("darkToggle");
  if (btn) {
    if (localStorage.theme === "dark") {
      document.body.classList.add("dark");
      btn.textContent = "Light Mode";
    } else {
      btn.textContent = "Dark Mode";
    }

    btn.addEventListener("click", () => {
      const isDark = document.body.classList.toggle("dark");
      localStorage.theme = isDark ? "dark" : "light";
      btn.textContent = isDark ? "Light Mode" : "Dark Mode";
    });
  }

  // ===== HIGHLIGHT ACTIVE NAV LINK =====
  document.querySelectorAll(".nav-link").forEach(link => {
    if (window.location.pathname === new URL(link.href).pathname) {
      link.classList.add("active");
    }
  });

  // ===== ITEM CARD CLICK HANDLER =====
  const cards = document.querySelectorAll(".item-card");
  console.log("FOUND CARDS:", cards.length);

  cards.forEach(card => {
    card.addEventListener("click", () => {
      const id = card.dataset.id;
      console.log("CLICKED CARD:", id);
      if (id) openItemModal(id);
      else console.error("Card has no data-id!");
    });
  });
});

// ===== OPEN MODAL AND FETCH ITEM =====
function openItemModal(id) {
  window.currentItemId = id;

  const modal = document.getElementById("itemModal");
  if (!modal) return console.error("Modal not found");

  modal.style.display = "flex";
  document.getElementById("modalName").innerText = "Loading...";
  document.getElementById("modalSku").innerText = "";
  document.getElementById("modalImage").src = "/static/placeholder.png";
  document.getElementById("modalBarcode").src = "";

  fetch(`/item/${id}`)
    .then(res => res.json())
    .then(data => {
      document.getElementById("modalName").innerText = data.name || "Unnamed Item";
      document.getElementById("modalSku").innerText = data.sku || "N/A";

      document.getElementById("modalManufacturer").value = data.manufacturer || "";
      document.getElementById("modalDimensions").value = data.dimensions || "";
      document.getElementById("modalColors").value = data.colorways || "";

      document.getElementById("modalCost").value = data.cost_price || "";
      document.getElementById("modalRetail").value = data.retail_price || "";
      document.getElementById("modalQtyInput").value = data.quantity || 0;

      document.getElementById("viewManufacturer").innerText = data.manufacturer || "";
      document.getElementById("viewDimensions").innerText = data.dimensions || "";
      document.getElementById("viewColors").innerText = data.colorways || "";

      // IMAGE AND BARCODE
      document.getElementById("modalImage").src = data.image_path || "/static/placeholder.png";
      document.getElementById("modalBarcode").src = data.barcode_path || "";

      // DELETE FORM
      const deleteForm = document.getElementById("deleteForm");
      if (deleteForm) deleteForm.action = `/delete-item/${data.id}`;

      // LABEL BUTTON
      const labelBtn = document.getElementById("generateLabelBtn");
      if (labelBtn) labelBtn.onclick = () => window.location.href = `/generate-label/${data.id}`;
    })
    .catch(err => {
      console.error("Failed to load item:", err);
      alert("Error loading item. Check console for details.");
    });
}

// ===== CLOSE MODAL =====
function closeItemModal() {
  const modal = document.getElementById("itemModal");
  if (modal) modal.style.display = "none";
}

// ===== QUANTITY ADJUST =====
window.adjustQty = function(change) {
  if (!window.currentItemId) return;
  fetch(`/adjust-quantity/${window.currentItemId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ change })
  })
  .then(res => res.json())
  .then(data => {
    const input = document.getElementById("modalQtyInput");
    if (input) input.value = data.new_quantity;
  });
}

// ===== SAVE ITEM CHANGES =====
function saveItemChanges() {
  if (!window.currentItemId) return;
  fetch(`/edit-item/${window.currentItemId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      manufacturer: document.getElementById("modalManufacturer").value,
      dimensions: document.getElementById("modalDimensions").value,
      colorways: document.getElementById("modalColors").value,
      cost_price: document.getElementById("modalCost").value,
      retail_price: document.getElementById("modalRetail").value
    })
  })
  .then(() => closeItemModal());
}

// ===== SCANNER MODAL =====
function openScanner() {
  document.getElementById("scannerModal").style.display = "flex";
}

function closeScanner() {
  document.getElementById("scannerModal").style.display = "none";
}
function toggleEditMode() {
  const fields = document.querySelectorAll(".edit-field");
  fields.forEach(input => {
    input.style.display = input.style.display === "block" ? "none" : "block";
  });

  const viewFields = ["viewManufacturer","viewDimensions","viewColors"];
  viewFields.forEach(id => {
    const p = document.getElementById(id);
    p.style.display = p.style.display === "none" ? "block" : "none";
  });
}
