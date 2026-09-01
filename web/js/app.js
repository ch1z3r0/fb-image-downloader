/**
 * Facebook Post Image Downloader Pro - Client Application Logic
 */

document.addEventListener("DOMContentLoaded", () => {
    // Initialize Lucide icons
    if (window.lucide) {
        window.lucide.createIcons();
    }

    // App State
    const state = {
        currentPostId: null,
        scrapedItems: [],
        selectedIndices: new Set(),
        currentLightboxIndex: 0,
        lastDownloadOutputDir: null,
        isScraping: false,
        progressTimerInterval: null,
    };

    // DOM Elements
    const elements = {
        scrapeForm: document.getElementById("scrapeForm"),
        fbUrlInput: document.getElementById("fbUrlInput"),
        btnPaste: document.getElementById("btnPaste"),
        btnSample: document.getElementById("btnSample"),
        btnSubmit: document.getElementById("btnSubmit"),
        btnTextToggle: document.getElementById("btnToggleSettings"),
        settingsDrawer: document.getElementById("settingsDrawer"),
        toggleChevron: document.querySelector(".toggle-chevron"),
        headlessToggle: document.getElementById("headlessToggle"),
        concurrencySlider: document.getElementById("concurrencySlider"),
        concurrencyLabel: document.getElementById("concurrencyLabel"),
        customOutputDir: document.getElementById("customOutputDir"),

        // Progress Section
        progressSection: document.getElementById("extractionProgressSection"),
        progressStatusText: document.getElementById("progressStatusText"),
        progressTimer: document.getElementById("progressTimer"),
        steps: [
            document.getElementById("step1"),
            document.getElementById("step2"),
            document.getElementById("step3"),
            document.getElementById("step4"),
        ],
        stepLines: [
            document.getElementById("line1"),
            document.getElementById("line2"),
            document.getElementById("line3"),
        ],

        // Gallery Section
        gallerySection: document.getElementById("gallerySection"),
        galleryTitle: document.getElementById("galleryTitle"),
        galleryPostId: document.getElementById("galleryPostId"),
        photosGrid: document.getElementById("photosGrid"),
        btnSelectAll: document.getElementById("btnSelectAll"),
        selectAllText: document.getElementById("selectAllText"),
        zipAlbumName: document.getElementById("zipAlbumName"),
        btnChooseFolder: document.getElementById("btnChooseFolder"),
        btnDownloadZip: document.getElementById("btnDownloadZip"),
        btnDownloadIndividual: document.getElementById("btnDownloadIndividual"),
        btnDownloadLocal: document.getElementById("btnDownloadLocal"),
        selectedCount: document.getElementById("selectedCount"),
        selectedCountPicker: document.getElementById("selectedCountPicker"),
        selectedCountZip: document.getElementById("selectedCountZip"),
        selectedCountFiles: document.getElementById("selectedCountFiles"),
        btnOpenFolder: document.getElementById("btnOpenFolder"),

        // Folder Guide Modal
        folderGuideModal: document.getElementById("folderGuideModal"),
        btnCloseFolderGuideModal: document.getElementById("btnCloseFolderGuideModal"),
        btnModalTriggerZip: document.getElementById("btnModalTriggerZip"),
        btnModalTriggerFiles: document.getElementById("btnModalTriggerFiles"),

        // Lightbox Elements
        lightboxModal: document.getElementById("lightboxModal"),
        lightboxImg: document.getElementById("lightboxImg"),
        lightboxIndex: document.getElementById("lightboxIndex"),
        lightboxDimensions: document.getElementById("lightboxDimensions"),
        btnLightboxPrev: document.getElementById("btnLightboxPrev"),
        btnLightboxNext: document.getElementById("btnLightboxNext"),
        btnLightboxClose: document.getElementById("btnLightboxClose"),
        btnLightboxDownload: document.getElementById("btnLightboxDownload"),
        btnLightboxCopy: document.getElementById("btnLightboxCopy"),

        // Health & Status
        healthStatusPill: document.getElementById("healthStatusPill"),
        healthStatusText: document.getElementById("healthStatusText"),
        btnHealthModal: document.getElementById("btnHealthModal"),
        healthModal: document.getElementById("healthModal"),
        btnCloseHealthModal: document.getElementById("btnCloseHealthModal"),
        modalChromiumStatus: document.getElementById("modalChromiumStatus"),
        modalOs: document.getElementById("modalOs"),
        modalPython: document.getElementById("modalPython"),
        modalDiskStatus: document.getElementById("modalDiskStatus"),
        modalNetworkUrl: document.getElementById("modalNetworkUrl"),
        toastContainer: document.getElementById("toastContainer"),
    };

    // 1. Initial Health Check
    fetchSystemHealth();

    // 2. Settings Drawer Toggle
    elements.btnTextToggle.addEventListener("click", () => {
        const isCollapsed = elements.settingsDrawer.classList.toggle("collapsed");
        elements.toggleChevron.style.transform = isCollapsed ? "rotate(0deg)" : "rotate(180deg)";
    });

    elements.concurrencySlider.addEventListener("input", (e) => {
        elements.concurrencyLabel.textContent = `${e.target.value} concurrent streams`;
    });

    // 3. Paste & Sample Helpers
    elements.btnPaste.addEventListener("click", async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                elements.fbUrlInput.value = text.trim();
                showToast("URL pasted from clipboard", "info");
            }
        } catch (err) {
            showToast("Clipboard access denied. Please paste manually.", "warning");
        }
    });

    elements.btnSample.addEventListener("click", () => {
        elements.fbUrlInput.value = "https://www.facebook.com/NASA/photos/a.10150125867961772/10160163935296772/";
        showToast("Sample Facebook post loaded", "info");
    });

    // 4. Scrape Form Submission
    elements.scrapeForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const url = elements.fbUrlInput.value.trim();
        if (!url) return;

        if (state.isScraping) return;
        state.isScraping = true;

        setScrapingState(true);
        startProgressStepper();

        try {
            const res = await fetch("/api/scrape", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url: url,
                    headless: elements.headlessToggle.checked,
                }),
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({ detail: "Scraping failed." }));
                throw new Error(errData.detail || `Server error: ${res.status}`);
            }

            const data = await res.json();
            stopProgressStepper(true);

            if (!data.items || data.items.length === 0) {
                if (data.is_private_or_deleted) {
                    showToast(
                        data.status_message || "🔒 This post is private, restricted, or has been deleted on Facebook.",
                        "error"
                    );
                } else {
                    showToast(data.status_message || "No high-resolution images found on this post.", "warning");
                }
                elements.gallerySection.classList.add("hidden");
                return;
            }

            state.currentPostId = data.post_id;
            state.scrapedItems = data.items;
            state.selectedIndices = new Set(data.items.map((_, idx) => idx));

            renderGallery(data);
            showToast(`Successfully extracted ${data.items.length} high-res photo(s)!`, "success");

        } catch (error) {
            stopProgressStepper(false);
            console.error("Scrape error:", error);
            showToast(error.message || "Failed to extract Facebook photos.", "error");
        } finally {
            state.isScraping = false;
            setScrapingState(false);
        }
    });

    // 5. Gallery Rendering
    function renderGallery(data) {
        elements.gallerySection.classList.remove("hidden");
        elements.galleryTitle.textContent = `Found ${data.items.length} High-Res Photo${data.items.length > 1 ? "s" : ""}`;
        elements.galleryPostId.textContent = `Post ID: ${data.post_id || "facebook_post"}`;
        updateSelectedCount();

        elements.photosGrid.innerHTML = "";

        data.items.forEach((item, idx) => {
            const card = document.createElement("div");
            card.className = "photo-card selected";
            card.id = `card-${idx}`;

            const dimText = item.width && item.height ? `${item.width} × ${item.height}` : "HD Photo";
            const extText = (item.mime_type || "image/jpeg").split("/")[1]?.toUpperCase() || "JPG";

            card.innerHTML = `
                <div class="card-img-container" data-index="${idx}">
                    <div class="card-checkbox-wrap">
                        <input type="checkbox" class="card-checkbox" data-index="${idx}" checked />
                    </div>
                    <span class="card-badge-index">#${idx + 1}</span>
                    <img src="${item.url}" alt="Post Photo #${idx + 1}" class="card-img" loading="lazy" />
                    <span class="card-badge-dim">${dimText} • ${extText}</span>
                </div>
                <div class="card-footer">
                    <span class="card-meta-text">photo_${String(idx + 1).padStart(3, "0")}</span>
                    <div class="card-actions">
                        <button type="button" class="btn-card-action btn-view-single" data-index="${idx}" title="Zoom Photo">
                            <i data-lucide="maximize-2"></i>
                        </button>
                        <button type="button" class="btn-card-action btn-dl-single" data-index="${idx}" title="Download">
                            <i data-lucide="download"></i>
                        </button>
                        <button type="button" class="btn-card-action btn-copy-single" data-url="${item.url}" title="Copy Link">
                            <i data-lucide="copy"></i>
                        </button>
                    </div>
                </div>
            `;

            elements.photosGrid.appendChild(card);
        });

        if (window.lucide) {
            window.lucide.createIcons();
        }

        // Attach Card Listeners
        attachCardListeners();

        // Scroll smoothly to gallery
        elements.gallerySection.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function attachCardListeners() {
        // Image Click opens Lightbox
        document.querySelectorAll(".card-img-container").forEach((el) => {
            el.addEventListener("click", (e) => {
                if (e.target.classList.contains("card-checkbox")) return;
                const idx = parseInt(el.getAttribute("data-index"), 10);
                openLightbox(idx);
            });
        });

        // Checkbox toggles
        document.querySelectorAll(".card-checkbox").forEach((cb) => {
            cb.addEventListener("change", (e) => {
                const idx = parseInt(cb.getAttribute("data-index"), 10);
                const card = document.getElementById(`card-${idx}`);
                if (cb.checked) {
                    state.selectedIndices.add(idx);
                    card.classList.add("selected");
                } else {
                    state.selectedIndices.delete(idx);
                    card.classList.remove("selected");
                }
                updateSelectedCount();
            });
        });

        // View single button
        document.querySelectorAll(".btn-view-single").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const idx = parseInt(btn.getAttribute("data-index"), 10);
                openLightbox(idx);
            });
        });

        // Download single button
        document.querySelectorAll(".btn-dl-single").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const idx = parseInt(btn.getAttribute("data-index"), 10);
                downloadSingleItem(idx);
            });
        });

        // Copy single link button
        document.querySelectorAll(".btn-copy-single").forEach((btn) => {
            btn.addEventListener("click", async (e) => {
                e.stopPropagation();
                const url = btn.getAttribute("data-url");
                try {
                    await navigator.clipboard.writeText(url);
                    showToast("CDN Image URL copied to clipboard", "success");
                } catch (err) {
                    showToast("Failed to copy link", "warning");
                }
            });
        });
    }

    // 6. Multi-Select & Batch Actions
    elements.btnSelectAll.addEventListener("click", () => {
        const allSelected = state.selectedIndices.size === state.scrapedItems.length;
        if (allSelected) {
            state.selectedIndices.clear();
            document.querySelectorAll(".card-checkbox").forEach((cb) => (cb.checked = false));
            document.querySelectorAll(".photo-card").forEach((c) => c.classList.remove("selected"));
            elements.selectAllText.textContent = "Select All";
        } else {
            state.selectedIndices = new Set(state.scrapedItems.map((_, i) => i));
            document.querySelectorAll(".card-checkbox").forEach((cb) => (cb.checked = true));
            document.querySelectorAll(".photo-card").forEach((c) => c.classList.add("selected"));
            elements.selectAllText.textContent = "Deselect All";
        }
        updateSelectedCount();
    });

    function updateSelectedCount() {
        const count = state.selectedIndices.size;
        if (elements.selectedCount) elements.selectedCount.textContent = count;
        if (elements.selectedCountPicker) elements.selectedCountPicker.textContent = count;
        if (elements.selectedCountZip) elements.selectedCountZip.textContent = count;
        if (elements.selectedCountFiles) elements.selectedCountFiles.textContent = count;

        if (elements.btnChooseFolder) elements.btnChooseFolder.disabled = count === 0;
        if (elements.btnDownloadLocal) elements.btnDownloadLocal.disabled = count === 0;
        if (elements.btnDownloadZip) elements.btnDownloadZip.disabled = count === 0;
        if (elements.btnDownloadIndividual) elements.btnDownloadIndividual.disabled = count === 0;

        if (elements.selectAllText) {
            elements.selectAllText.textContent =
                count === state.scrapedItems.length ? "Deselect All" : "Select All";
        }
    }

    // 7. Save Directly into User-Selected Local Folder (Native File System Access)
    if (elements.btnChooseFolder) {
        elements.btnChooseFolder.addEventListener("click", async () => {
            const selectedItems = Array.from(state.selectedIndices).map((i) => state.scrapedItems[i]);
            if (selectedItems.length === 0) return;

            // Check if Native Directory Picker is available in this browser context
            if (window.isSecureContext && "showDirectoryPicker" in window) {
                try {
                    const dirHandle = await window.showDirectoryPicker({
                        id: "fb_photos_downloader",
                        mode: "readwrite",
                    });

                    showToast(`Saving ${selectedItems.length} photos to: "${dirHandle.name}" on your computer...`, "info");

                    let savedCount = 0;
                    for (let i = 0; i < selectedItems.length; i++) {
                        const item = selectedItems[i];
                        const ext = getExtensionFromUrl(item.url);
                        const filename = item.suggested_filename || `photo_${String(i + 1).padStart(3, "0")}${ext}`;
                        const downloadUrl = `/api/download-single?url=${encodeURIComponent(item.url)}&filename=${encodeURIComponent(filename)}`;

                        try {
                            const res = await fetch(downloadUrl);
                            if (!res.ok) continue;
                            const blob = await res.blob();
                            const fileHandle = await dirHandle.getFileHandle(filename, { create: true });
                            const writable = await fileHandle.createWritable();
                            await writable.write(blob);
                            await writable.close();
                            savedCount++;

                            if ((i + 1) % 5 === 0 || i === selectedItems.length - 1) {
                                showToast(`Saved ${savedCount} of ${selectedItems.length} photos to "${dirHandle.name}"...`, "info");
                            }
                        } catch (itemErr) {
                            console.error(`Failed to write ${filename}:`, itemErr);
                        }
                    }

                    showToast(`🎉 Successfully saved ${savedCount} photos directly to folder "${dirHandle.name}"!`, "success");
                } catch (err) {
                    if (err.name !== "AbortError") {
                        console.error("Directory picker error:", err);
                        // Open helper guide
                        if (elements.folderGuideModal) elements.folderGuideModal.classList.remove("hidden");
                    }
                }
            } else {
                // Not in Secure Context (HTTP LAN) or unsupported browser - open guide modal
                if (elements.folderGuideModal) {
                    elements.folderGuideModal.classList.remove("hidden");
                } else {
                    elements.btnDownloadZip.click();
                }
            }
        });
    }

    // Folder Guide Modal Controls
    if (elements.btnCloseFolderGuideModal) {
        elements.btnCloseFolderGuideModal.addEventListener("click", () => {
            elements.folderGuideModal.classList.add("hidden");
        });
    }
    if (elements.btnModalTriggerZip) {
        elements.btnModalTriggerZip.addEventListener("click", () => {
            elements.folderGuideModal.classList.add("hidden");
            elements.btnDownloadZip.click();
        });
    }
    if (elements.btnModalTriggerFiles) {
        elements.btnModalTriggerFiles.addEventListener("click", () => {
            elements.folderGuideModal.classList.add("hidden");
            if (elements.btnDownloadIndividual) elements.btnDownloadIndividual.click();
        });
    }
    if (elements.folderGuideModal) {
        elements.folderGuideModal.addEventListener("click", (e) => {
            if (e.target === elements.folderGuideModal) {
                elements.folderGuideModal.classList.add("hidden");
            }
        });
    }

    // 7b. Download ZIP in Browser
    elements.btnDownloadZip.addEventListener("click", async () => {
        const selectedItems = Array.from(state.selectedIndices).map((i) => state.scrapedItems[i]);
        if (selectedItems.length === 0) return;

        const albumName = elements.zipAlbumName ? elements.zipAlbumName.value.trim() : "";
        showToast(
            `Bundling ${selectedItems.length} photos into ${albumName ? `folder "${albumName}"` : "ZIP archive"}...`,
            "info"
        );
        try {
            const res = await fetch("/api/download-zip", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    post_id: state.currentPostId || "photos",
                    items: selectedItems,
                    folder_name: albumName || null,
                }),
            });

            if (!res.ok) throw new Error("ZIP creation failed on server.");

            const blob = await res.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = downloadUrl;
            a.download = albumName ? `${albumName}.zip` : `facebook_${state.currentPostId || "photos"}.zip`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(downloadUrl);

            showToast("ZIP archive downloaded to your device!", "success");
        } catch (err) {
            console.error("ZIP download failed:", err);
            showToast("Failed to download ZIP archive.", "error");
        }
    });

    // 7b. Download Individual Files to Client Device
    if (elements.btnDownloadIndividual) {
        elements.btnDownloadIndividual.addEventListener("click", async () => {
            const selectedIndices = Array.from(state.selectedIndices);
            if (selectedIndices.length === 0) return;

            showToast(`Downloading ${selectedIndices.length} individual image(s) to your device...`, "info");
            for (let i = 0; i < selectedIndices.length; i++) {
                const idx = selectedIndices[i];
                await downloadSingleItem(idx);
                // Stagger requests to ensure browser queues downloads smoothly
                await new Promise((r) => setTimeout(r, 220));
            }
            showToast(`Completed sending ${selectedIndices.length} photo(s) to your device!`, "success");
        });
    }

    // 8. Download to Local Disk with Customizable Folder
    elements.galleryOutputDir = document.getElementById("galleryOutputDir");

    // Sync path inputs
    if (elements.customOutputDir && elements.galleryOutputDir) {
        elements.customOutputDir.addEventListener("input", (e) => {
            elements.galleryOutputDir.value = e.target.value;
        });
        elements.galleryOutputDir.addEventListener("input", (e) => {
            elements.customOutputDir.value = e.target.value;
        });
    }

    // Path Presets Chips
    document.querySelectorAll(".preset-chip").forEach((chip) => {
        chip.addEventListener("click", () => {
            const path = chip.getAttribute("data-path");
            if (path) {
                if (elements.galleryOutputDir) elements.galleryOutputDir.value = path;
                if (elements.customOutputDir) elements.customOutputDir.value = path;
                showToast(`Save location set to: ${path}`, "info");
            }
        });
    });

    elements.btnDownloadLocal.addEventListener("click", async () => {
        const selectedItems = Array.from(state.selectedIndices).map((i) => state.scrapedItems[i]);
        if (selectedItems.length === 0) return;

        const concurrency = parseInt(elements.concurrencySlider.value, 10) || 5;
        const customDir =
            (elements.galleryOutputDir && elements.galleryOutputDir.value.trim()) ||
            (elements.customOutputDir && elements.customOutputDir.value.trim()) ||
            null;

        showToast(`Downloading ${selectedItems.length} photos to: ${customDir || "./downloads"}...`, "info");

        try {
            const res = await fetch("/api/download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    post_id: state.currentPostId || "facebook_post",
                    items: selectedItems,
                    output_dir: customDir,
                    concurrency: concurrency,
                }),
            });

            if (!res.ok) throw new Error("Download failed on server.");
            const data = await res.json();

            state.lastDownloadOutputDir = data.output_dir;
            elements.btnOpenFolder.classList.remove("hidden");
            elements.btnOpenFolder.scrollIntoView({ behavior: "smooth", block: "nearest" });

            const sizeMb = (data.total_bytes / (1024 * 1024)).toFixed(2);
            showToast(
                `Saved ${data.successful_items.length} photos (${sizeMb} MB) to: ${data.output_dir}`,
                "success"
            );
        } catch (err) {
            console.error("Local download failed:", err);
            showToast("Failed to download media to disk.", "error");
        }
    });

    // 9. Open Folder in Finder/Explorer
    elements.btnOpenFolder.addEventListener("click", async () => {
        if (!state.lastDownloadOutputDir) return;
        try {
            const res = await fetch("/api/open-folder", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: state.lastDownloadOutputDir }),
            });
            if (res.ok) {
                showToast(`Opened folder in File Manager: ${state.lastDownloadOutputDir}`, "info");
            } else {
                showToast("Could not open folder automatically.", "warning");
            }
        } catch (err) {
            console.error("Open folder error:", err);
        }
    });

    function getExtensionFromUrl(url) {
        const u = (url || "").toLowerCase();
        if (u.includes("dst-png") || u.includes(".png")) return ".png";
        if (u.includes("dst-webp") || u.includes(".webp")) return ".webp";
        if (u.includes("dst-avif") || u.includes(".avif")) return ".avif";
        if (u.includes(".gif")) return ".gif";
        if (u.includes(".bmp")) return ".bmp";
        if (u.includes(".svg")) return ".svg";
        return ".jpg";
    }

    async function downloadSingleItem(index) {
        const item = state.scrapedItems[index];
        if (!item) return;
        try {
            const ext = getExtensionFromUrl(item.url);
            const filename = item.suggested_filename || `photo_${String(index + 1).padStart(3, "0")}${ext}`;
            const downloadUrl = `/api/download-single?url=${encodeURIComponent(item.url)}&filename=${encodeURIComponent(filename)}`;

            const res = await fetch(downloadUrl);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const blob = await res.blob();
            const blobUrl = window.URL.createObjectURL(blob);

            const a = document.createElement("a");
            a.style.display = "none";
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();

            setTimeout(() => {
                a.remove();
                window.URL.revokeObjectURL(blobUrl);
            }, 1500);

            showToast(`Downloaded photo #${index + 1} (${ext.toUpperCase()}) to your device`, "success");
        } catch (err) {
            console.error("Single download error:", err);
            showToast(`Could not download photo #${index + 1} to your device.`, "warning");
        }
    }

    // 10. Lightbox Logic
    function openLightbox(index) {
        if (!state.scrapedItems[index]) return;
        state.currentLightboxIndex = index;
        updateLightboxContent();
        elements.lightboxModal.classList.remove("hidden");
        document.body.style.overflow = "hidden";
    }

    function closeLightbox() {
        elements.lightboxModal.classList.add("hidden");
        document.body.style.overflow = "auto";
    }

    function updateLightboxContent() {
        const item = state.scrapedItems[state.currentLightboxIndex];
        if (!item) return;

        elements.lightboxImg.src = item.url;
        elements.lightboxIndex.textContent = `Photo ${state.currentLightboxIndex + 1} of ${state.scrapedItems.length}`;
        elements.lightboxDimensions.textContent =
            item.width && item.height ? `${item.width} × ${item.height} px` : "High Resolution";
    }

    elements.btnLightboxPrev.addEventListener("click", () => {
        if (state.currentLightboxIndex > 0) {
            state.currentLightboxIndex--;
            updateLightboxContent();
        } else {
            state.currentLightboxIndex = state.scrapedItems.length - 1;
            updateLightboxContent();
        }
    });

    elements.btnLightboxNext.addEventListener("click", () => {
        if (state.currentLightboxIndex < state.scrapedItems.length - 1) {
            state.currentLightboxIndex++;
            updateLightboxContent();
        } else {
            state.currentLightboxIndex = 0;
            updateLightboxContent();
        }
    });

    elements.btnLightboxClose.addEventListener("click", closeLightbox);
    elements.lightboxModal.querySelector(".lightbox-backdrop").addEventListener("click", closeLightbox);

    elements.btnLightboxDownload.addEventListener("click", () => {
        downloadSingleItem(state.currentLightboxIndex);
    });

    elements.btnLightboxCopy.addEventListener("click", async () => {
        const item = state.scrapedItems[state.currentLightboxIndex];
        if (item) {
            await navigator.clipboard.writeText(item.url);
            showToast("Image URL copied to clipboard", "success");
        }
    });

    // Keyboard Shortcuts for Lightbox
    window.addEventListener("keydown", (e) => {
        if (elements.lightboxModal.classList.contains("hidden")) return;
        if (e.key === "Escape") closeLightbox();
        if (e.key === "ArrowLeft") elements.btnLightboxPrev.click();
        if (e.key === "ArrowRight") elements.btnLightboxNext.click();
    });

    // 11. System Health Modal
    elements.btnHealthModal.addEventListener("click", () => {
        fetchSystemHealth();
        elements.healthModal.classList.remove("hidden");
    });

    elements.btnCloseHealthModal.addEventListener("click", () => {
        elements.healthModal.classList.add("hidden");
    });

    elements.healthModal.addEventListener("click", (e) => {
        if (e.target === elements.healthModal) {
            elements.healthModal.classList.add("hidden");
        }
    });

    async function fetchSystemHealth() {
        try {
            const res = await fetch("/api/health");
            const data = await res.json();
            if (data.status === "healthy") {
                elements.healthStatusPill.className = "status-pill ready";
                elements.healthStatusText.textContent = "Engine Ready";
                elements.modalChromiumStatus.textContent = "Installed & Ready";
                elements.modalChromiumStatus.className = "status-val text-green";
            } else {
                elements.healthStatusPill.className = "status-pill";
                elements.healthStatusText.textContent = "Setup Required";
                elements.modalChromiumStatus.textContent = data.message || "Not ready";
                elements.modalChromiumStatus.className = "status-val";
            }
            elements.modalOs.textContent = data.os || "macOS";
            elements.modalPython.textContent = data.python_version || "3.9+";
            if (elements.modalNetworkUrl) {
                elements.modalNetworkUrl.textContent = data.network_url || "http://localhost:8000";
            }
        } catch (err) {
            elements.healthStatusPill.className = "status-pill";
            elements.healthStatusText.textContent = "Offline";
        }
    }

    // 12. Helper Animations & Stepper
    function setScrapingState(isScraping) {
        elements.btnSubmit.disabled = isScraping;
        const btnText = elements.btnSubmit.querySelector(".btn-text");
        const btnLoader = elements.btnSubmit.querySelector(".btn-loader");
        if (isScraping) {
            btnText.classList.add("hidden");
            btnLoader.classList.remove("hidden");
        } else {
            btnText.classList.remove("hidden");
            btnLoader.classList.add("hidden");
        }
    }

    function startProgressStepper() {
        elements.progressSection.classList.remove("hidden");
        let seconds = 0;
        elements.progressTimer.textContent = "0s elapsed";

        if (state.progressTimerInterval) clearInterval(state.progressTimerInterval);
        state.progressTimerInterval = setInterval(() => {
            seconds++;
            elements.progressTimer.textContent = `${seconds}s elapsed`;

            // Step progression simulation
            if (seconds === 1) activateStep(0);
            if (seconds === 2) activateStep(1);
            if (seconds === 4) activateStep(2);
            if (seconds === 6) activateStep(3);
        }, 1000);
    }

    function activateStep(idx) {
        elements.steps.forEach((step, i) => {
            if (i < idx) {
                step.className = "step-node completed";
            } else if (i === idx) {
                step.className = "step-node active";
            } else {
                step.className = "step-node";
            }
        });
        elements.stepLines.forEach((line, i) => {
            line.className = i < idx ? "step-line active" : "step-line";
        });
    }

    function stopProgressStepper(success) {
        if (state.progressTimerInterval) {
            clearInterval(state.progressTimerInterval);
            state.progressTimerInterval = null;
        }
        if (success) {
            elements.steps.forEach((s) => (s.className = "step-node completed"));
            elements.stepLines.forEach((l) => (l.className = "step-line active"));
            elements.progressStatusText.textContent = "Extraction completed successfully!";
            setTimeout(() => {
                elements.progressSection.classList.add("hidden");
            }, 2500);
        } else {
            elements.progressSection.classList.add("hidden");
        }
    }

    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.textContent = message;
        elements.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(100%)";
            toast.style.transition = "all 0.3s ease";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // Auto-populate URL from query parameters if navigated from tutorial
    const urlParams = new URLSearchParams(window.location.search);
    const queryUrl = urlParams.get("url");
    if (queryUrl) {
        elements.fbUrlInput.value = queryUrl;
        showToast("Loaded link from Tutorial! Click 'Extract Photos' to begin.", "info");
        elements.fbUrlInput.scrollIntoView({ behavior: "smooth", block: "center" });
        elements.fbUrlInput.focus();
    }
});
