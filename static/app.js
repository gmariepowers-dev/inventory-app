let html5QrCode = null;
window.currentItemId = null;

document.addEventListener("DOMContentLoaded", () => {

  // SEARCH
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      const query = searchInput.value.toLowerCase();
      document.querySelectorAll(".item-card").forEach(card => {
        card.style.display = card.innerText.toLowerCase().includes(query) ? "flex" : "none";
      });
    });
  }

  // ITEM CLICK
  document.querySelectorAll(".item-card").forEach(card => {
    card.addEventListener("click", () => {
      const id = card.dataset.id;
      if (id) openItemModal(id);
    });
  });

});

function openItemModal(id) {
  window.currentItemId = id;

  const modal = document.getElementById("itemModal");
  modal.style.display = "flex";

  fetch(`/item/${id}`)
    .then(res => res.json())
    .then(data => {

      // SAFE FIELD SETTING (prevents crashes)
      const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.innerText = value || "";
      };

      const setValue = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.value = value || "";
      };

      setText("modalName", data.name);
      setText("modalSku", data.sku);
      setText("viewManufacturer", data.manufacturer);
      setText("viewDimensions", data.dimensions);
      setText("viewColors", data.colorways);
      setText("viewCost", data.cost_price);
      setText("viewRetail", data.retail_price);
      setText("viewQty", data.quantity);
      setText("viewWeight", data.weight);

      setValue("modalManufacturer", data.manufacturer);
      setValue("modalDimensions", data.dimensions);
      setValue("modalColors", data.colorways);
      setValue("modalCost", data.cost_price);
      setValue("modalRetail", data.retail_price);
      setValue("modalQtyInput", data.quantity);
      setValue("modalWeight", data.weight);

      // IMAGE + BARCODE SAFE
      document.getElementById("modalImage").src = data.image_path || "/static/placeholder.png";
      document.getElementById("modalBarcode").src = data.barcode_path || "";

      document.addEventListener("input", (e) => {
        if (e.target.id === "modalQtyInput") {
          const val = e.target.value;
          document.getElementById("viewQty").innerText = val;
        }
      });

 // label button FIX
      const labelBtn = document.getElementById("generateLabelBtn");
      if (labelBtn) {
        labelBtn.onclick = () => {
          window.location.href = `/generate-label/${data.id}`;
        };
      }

      resetEditMode();
    });
}

function closeItemModal() {
  document.getElementById("itemModal").style.display = "none";
}

function toggleEditMode() {
  const editing = document.body.classList.toggle("editing");

  document.querySelectorAll(".edit-field").forEach(el => {
    el.style.display = editing ? "block" : "none";
  });

  document.querySelectorAll(".field p").forEach(el => {
    el.style.display = editing ? "none" : "block";
  });

  const saveBtn = document.getElementById("saveBtn");
  if (saveBtn) saveBtn.style.display = editing ? "inline-block" : "none";
}

function resetEditMode() {
  document.body.classList.remove("editing");

  document.querySelectorAll(".edit-field").forEach(el => {
    el.style.display = "none";
  });

  document.querySelectorAll(".field p").forEach(el => {
    el.style.display = "block";
  });

  const saveBtn = document.getElementById("saveBtn");
  if (saveBtn) saveBtn.style.display = "none";
}

function saveItemChanges() {
  if (!window.currentItemId) return;

  fetch(`/edit-item/${window.currentItemId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      manufacturer: modalManufacturer.value,
      dimensions: modalDimensions.value,
      colorways: modalColors.value,
      cost_price: modalCost.value,
      retail_price: modalRetail.value,
      weight: modalWeight.value
    })
  })
  .then(() => {
    // 🔥 UPDATE UI AFTER SAVE
    viewManufacturer.innerText = modalManufacturer.value;
    viewDimensions.innerText = modalDimensions.value;
    viewColors.innerText = modalColors.value;
    viewCost.innerText = modalCost.value;
    viewRetail.innerText = modalRetail.value;
    viewWeight.innerText = modalWeight.value;

    resetEditMode();
  });
}

function adjustQty(change) {
  fetch(`/adjust-quantity/${window.currentItemId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ change })
  })
  .then(res => res.json())
  .then(data => {
    viewQty.innerText = data.new_quantity;
    modalQtyInput.value = data.new_quantity;
  });
}

function openScanner() {
  const modal = document.getElementById("scannerModal");
  modal.style.display = "flex";

  setTimeout(() => {
    html5QrCode = new Html5Qrcode("scanner");

    html5QrCode.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: 250 },
      (text) => {
        window.location.href = `/scan/${text}`;
      }
    );
  }, 500);
}

function closeScanner() {
  document.getElementById("scannerModal").style.display = "none";
  if (html5QrCode) html5QrCode.stop().catch(() => {});
}