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

    const params = new URLSearchParams(window.location.search);
  const openItemId = params.get("open_item");

  if (openItemId) {
    openItemModal(openItemId);

    const cleanUrl = window.location.pathname;
    window.history.replaceState({}, document.title, cleanUrl);
  }

  // LIVE quantity input update
  document.addEventListener("input", (e) => {
    if (e.target.id === "modalQtyInput") {
      const val = e.target.value;
      const viewQty = document.getElementById("viewQty");
      if (viewQty) viewQty.innerText = val || "0";
      updateTotalRetailPreview();
    }

    if (e.target.id === "modalRetail") {
      updateTotalRetailPreview();
    }
  });
});

function formatCurrency(value) {
  return `$${(parseFloat(value) || 0).toFixed(2)}`;
}

function updateTotalRetailPreview() {
  const qtyInput = document.getElementById("modalQtyInput");
  const retailInput = document.getElementById("modalRetail");
  const totalRetailEl = document.getElementById("viewTotalRetail");

  if (!totalRetailEl) return;

  const qty = parseFloat(qtyInput?.value || 0);
  const retail = parseFloat(retailInput?.value || 0);

  totalRetailEl.innerText = formatCurrency(qty * retail);
}

function openItemModal(id) {
  window.currentItemId = id;

  const modal = document.getElementById("itemModal");
  modal.style.display = "flex";

  fetch(`/item/${id}`)
    .then(res => res.json())
    .then(data => {
      const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.innerText = value ?? "";
      };

      const setValue = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.value = value ?? "";
      };

      setText("modalName", data.name);
      setText("modalSku", data.sku);
      setText("viewManufacturer", data.manufacturer);
      setText("viewDimensions", data.dimensions);
      setText("viewColors", data.colorways);
      setText("viewWeight", data.weight);

      setText("viewCost", formatCurrency(data.cost_price));
      setText("viewRetail", formatCurrency(data.retail_price));
      setText("viewQty", data.quantity);
      setText("viewTotalRetail", formatCurrency(data.total_retail_value));

      setValue("modalManufacturer", data.manufacturer);
      setValue("modalDimensions", data.dimensions);
      setValue("modalColors", data.colorways);
      setValue("modalCost", data.cost_price);
      setValue("modalRetail", data.retail_price);
      setValue("modalQtyInput", data.quantity);
      setValue("modalWeight", data.weight);

      const modalImage = document.getElementById("modalImage");
      const modalBarcode = document.getElementById("modalBarcode");

      if (modalImage) {
        modalImage.src = data.image_path || "/static/placeholder.png";
      }

      if (modalBarcode) {
        modalBarcode.src = data.barcode_path || "";
      }

      const labelBtn = document.getElementById("generateLabelBtn");
      if (labelBtn) {
        labelBtn.onclick = () => {
          window.location.href = `/labels/item/${data.id}`;
        };
      }
      
      resetEditMode();
      updateTotalRetailPreview();
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
  if (saveBtn) saveBtn.style.display = editing ? "inline-flex" : "none";

  updateTotalRetailPreview();
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

  const modalManufacturer = document.getElementById("modalManufacturer");
  const modalDimensions = document.getElementById("modalDimensions");
  const modalColors = document.getElementById("modalColors");
  const modalCost = document.getElementById("modalCost");
  const modalRetail = document.getElementById("modalRetail");
  const modalWeight = document.getElementById("modalWeight");

  const viewManufacturer = document.getElementById("viewManufacturer");
  const viewDimensions = document.getElementById("viewDimensions");
  const viewColors = document.getElementById("viewColors");
  const viewCost = document.getElementById("viewCost");
  const viewRetail = document.getElementById("viewRetail");
  const viewWeight = document.getElementById("viewWeight");

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
    .then(res => res.json())
    .then(() => {
      if (viewManufacturer) viewManufacturer.innerText = modalManufacturer.value;
      if (viewDimensions) viewDimensions.innerText = modalDimensions.value;
      if (viewColors) viewColors.innerText = modalColors.value;
      if (viewCost) viewCost.innerText = formatCurrency(modalCost.value);
      if (viewRetail) viewRetail.innerText = formatCurrency(modalRetail.value);
      if (viewWeight) viewWeight.innerText = modalWeight.value;

      updateTotalRetailPreview();
      resetEditMode();
    });
}

function adjustQty(change) {
  if (!window.currentItemId) return;

  fetch(`/adjust-quantity/${window.currentItemId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ change })
  })
    .then(res => res.json())
    .then(data => {
      const viewQty = document.getElementById("viewQty");
      const modalQtyInput = document.getElementById("modalQtyInput");

      if (viewQty) viewQty.innerText = data.new_quantity;
      if (modalQtyInput) modalQtyInput.value = data.new_quantity;

      updateTotalRetailPreview();
    });
}

function openScanner() {
  const modal = document.getElementById("scannerModal");
  if (!modal) return;

  modal.style.display = "flex";

  setTimeout(() => {
    if (html5QrCode) {
      html5QrCode.stop().catch(() => {});
      html5QrCode = null;
    }

    html5QrCode = new Html5Qrcode("scanner");

    html5QrCode.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: 250 },
      (text) => {
        handleScannedCode(text);
      }
    );
  }, 300);
}

function handleScannedCode(text) {
  fetch(`/scan/${encodeURIComponent(text)}`)
    .then(res => res.json())
    .then(data => {
      closeScanner();

      if (!data.found) {
        alert("No matching item found.");
        return;
      }

      const itemCard = document.querySelector(`.item-card[data-id="${data.id}"]`);

      if (itemCard) {
        openItemModal(data.id);
      } else {
        window.location.href = `/?open_item=${data.id}`;
      }
    })
    .catch(() => {
      closeScanner();
      alert("There was a problem scanning that item.");
    });
}

function closeScanner() {
  const modal = document.getElementById("scannerModal");
  if (modal) modal.style.display = "none";

  if (html5QrCode) {
    html5QrCode.stop()
      .then(() => {
        html5QrCode.clear?.();
        html5QrCode = null;
      })
      .catch(() => {
        html5QrCode = null;
      });
  }
}