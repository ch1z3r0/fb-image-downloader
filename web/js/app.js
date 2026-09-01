/**
 * Facebook Post Image Downloader Pro - Client Application Logic
 * High-End State Handling, Skeletons, Session HUD, Floating Action Dock & Lightbox
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

        // Progress Section & Live Session HUD
        progressSection: document.getElementById("extractionProgressSection"),
        progressStatusText: document.getElementById("progressStatusText"),
        progressTimer: document.getElementById("progressTimer"),
        btnToggleLogs: document.getElementById("btnToggleLogs"),
        chevronLogs: document.getElementById("chevronLogs"),
        sessionLogDrawer: document.getElementById("sessionLogDrawer"),
        sessionLogConsole: document.getElementById("sessionLogConsole"),
        btnCopyLogs: document.getElementById("btnCopyLogs"),
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
        galleryOutputDir: document.getElementById("galleryOutputDir"),

        // Floating Bottom Action Dock
        floatingActionDock: document.getElementById("floatingActionDock"),
        dockSelectedCount: document.getElementById("dockSelectedCount"),
        dockCountZip: document.getElementById("dockCountZip"),
        btnDockSelectAll: document.getElementById("btnDockSelectAll"),
        btnDockClearAll: document.getElementById("btnDockClearAll"),
        btnDockDownloadZip: document.getElementById("btnDockDownloadZip"),
        btnDockSaveLocal: document.getElementById("btnDockSaveLocal"),

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
        lightboxMime: document.getElementById("lightboxMime"),
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
    if (elements.btnTextToggle) {
        elements.btnTextToggle.addEventListener("click", () => {
            const isCollapsed = elements.settingsDrawer.classList.toggle("collapsed");
            if (elements.toggleChevron) {
                elements.toggleChevron.style.transform = isCollapsed ? "rotate(0deg)" : "rotate(180deg)";
            }
        });
    }

    if (elements.concurrencySlider) {
        elements.concurrencySlider.addEventListener("input", (e) => {
            elements.concurrencyLabel.textContent = `${e.target.value} concurrent streams`;
        });
    }

    // 3. Session Log HUD Drawer Toggle & Copy
    if (elements.btnToggleLogs) {
        elements.btnToggleLogs.addEventListener("click", () => {
            const isCollapsed = elements.sessionLogDrawer.classList.toggle("collapsed");
            if (elements.chevronLogs) {
                elements.chevronLogs.style.transform = isCollapsed ? "rotate(0deg)" : "rotate(180deg)";
            }
        });
    }

    if (elements.btnCopyLogs) {
        elements.btnCopyLogs.addEventListener("click", async () => {
            const logText = elements.sessionLogConsole ? elements.sessionLogConsole.innerText : "";
            if (logText) {
                try {
                    await navigator.clipboard.writeText(logText);
                    showToast("Engine session logs copied to clipboard", "success");
                } catch (err) {
                    showToast("Failed to copy logs to clipboard", "warning");
                }
            }
        });
    }

    function appendLog(message, type = "info") {
        if (!elements.sessionLogConsole) return;
        const line = document.createElement("div");
        line.className = "log-line";
        const time = new Date().toLocaleTimeString();
        let tagClass = "log-tag-scraper";
        if (type === "playwright") tagClass = "log-tag-playwright";
        if (type === "success") tagClass = "log-tag-success";
        if (type === "warn") tagClass = "log-tag-warn";
        if (type === "error") tagClass = "log-tag-error";

        line.innerHTML = `<span class="text-muted">[${time}]</span> <span class="${tagClass}">${escapeHtml(message)}</span>`;
        elements.sessionLogConsole.appendChild(line);
        elements.sessionLogConsole.scrollTop = elements.sessionLogConsole.scrollHeight;
    }

    function escapeHtml(str) {
        return (str || "").replace(/[&<>"']/g, (m) => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        })[m]);
    }

    // 4. Paste & Sample Helpers
    if (elements.btnPaste) {
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
    }

    if (elements.btnSample) {
        elements.btnSample.addEventListener("click", () => {
            elements.fbUrlInput.value = "https://www.facebook.com/NASA/photos/a.10150125867961772/10160163935296772/";
            showToast("Sample Facebook post loaded", "info");
        });
    }

    // 5. Scrape Form Submission with Skeleton State
    elements.scrapeForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const url = elements.fbUrlInput.value.trim();
        if (!url) return;

        if (state.isScraping) return;
        state.isScraping = true;

        setScrapingState(true);
        startProgressStepper();
        renderSkeletons(6);

        appendLog(`[Scraper] Initialized extraction for target: ${url}`, "playwright");

        try {
            const res = await fetch("/api/scrape", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url: url,
                    headless: elements.headlessToggle ? elements.headlessToggle.checked : true,
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
                    appendLog("[Error] Post is private, restricted, or has been deleted.", "error");
                    showToast(
                        data.status_message || "🔒 This post is private, restricted, or has been deleted on Facebook.",
                        "error"
                    );
                } else {
                    appendLog("[Warning] No high-resolution images discovered on target post.", "warn");
                    showToast(data.status_message || "No high-resolution images found on this post.", "warning");
                }
                elements.gallerySection.classList.add("hidden");
                updateSelectedCount();
                return;
            }

            state.currentPostId = data.post_id;
            state.scrapedItems = data.items;
            state.selectedIndices = new Set(data.items.map((_, idx) => idx));

            appendLog(`[Success] Discovered and resolved ${data.items.length} uncompressed photo asset(s) (Post ID: ${data.post_id})`, "success");
            renderGallery(data);
            showToast(`Successfully extracted ${data.items.length} high-res photo(s)!`, "success");

        } catch (error) {
            stopProgressStepper(false);
            appendLog(`[Error] ${error.message || "Failed to extract Facebook photos."}`, "error");
            console.error("Scrape error:", error);
            showToast(error.message || "Failed to extract Facebook photos.", "error");
            elements.gallerySection.classList.add("hidden");
            updateSelectedCount();
        } finally {
            state.isScraping = false;
            setScrapingState(false);
        }
    });

    // 6. Fluid Shimmer/Skeleton Loading State
    function renderSkeletons(count = 6) {
        elements.gallerySection.classList.remove("hidden");
        elements.galleryTitle.textContent = "Inspecting Facebook Media Grid...";
        elements.galleryPostId.textContent = "Playwright Automation Active";
        elements.photosGrid.innerHTML = "";
        if (elements.floatingActionDock) elements.floatingActionDock.classList.add("hidden");

        for (let i = 0; i < count; i++) {
            const skel = document.createElement("div");
            skel.className = "photo-card-skeleton";
            skel.innerHTML = `
                <div class="skeleton-shimmer skeleton-img">
                    <i data-lucide="image" class="icon-sm"></i>
                </div>
                <div class="skeleton-footer">
                    <div class="skeleton-shimmer skeleton-pill"></div>
                    <div class="skeleton-actions">
                        <div class="skeleton-shimmer skeleton-btn"></div>
                        <div class="skeleton-shimmer skeleton-btn"></div>
                    </div>
                </div>
            `;
            elements.photosGrid.appendChild(skel);
        }
        if (window.lucide) window.lucide.createIcons();
    }

    // 7. Gallery Rendering
    function renderGallery(data) {
        elements.gallerySection.classList.remove("hidden");
        elements.galleryTitle.textContent = `Found ${data.items.length} High-Res Photo${data.items.length > 1 ? "s" : ""}`;
        elements.galleryPostId.textContent = `Post ID: ${data.post_id || "facebook_post"}`;
        elements.photosGrid.innerHTML = "";

        data.items.forEach((item, idx) => {
            const card = document.createElement("div");
            card.className = "photo-card selected";
            card.id = `card-${idx}`;
            card.style.animationDelay = `${idx * 35}ms`;

            const dimText = item.width && item.height ? `${item.width} × ${item.height}` : "HD Photo";
            const extText = (item.mime_type || "image/jpeg").split("/")[1]?.toUpperCase() || "JPG";

            card.innerHTML = `
                <div class="card-img-container" data-index="${idx}">
                    <div class="card-checkbox-wrap">
                        <input type="checkbox" class="card-checkbox" data-index="${idx}" checked />
                    </div>
                    <span class="card-badge-index">#${idx + 1}</span>
                    <img src="${item.url}" alt="Post Photo #${idx + 1}" class="card-img" loading="lazy" />
                    <div class="card-img-overlay"></div>
                    <div class="card-hover-actions">
                        <button type="button" class="btn-hover-action btn-view-single" data-index="${idx}" title="Preview full-resolution photo">
                            <i data-lucide="maximize-2" class="icon-sm"></i> Inspect
                        </button>
                        <button type="button" class="btn-hover-action btn-dl-single" data-index="${idx}" title="Download single photo">
                            <i data-lucide="download" class="icon-sm"></i> Save
                        </button>
                    </div>
                    <span class="card-badge-dim font-mono">${dimText} • ${extText}</span>
                </div>
                <div class="card-footer">
                    <span class="card-meta-text font-mono">photo_${String(idx + 1).padStart(3, "0")}</span>
                    <div class="card-actions">
                        <button type="button" class="btn-card-action btn-view-single" data-index="${idx}" title="Inspect Photo">
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
        updateSelectedCount();

        // Scroll smoothly to gallery
        elements.gallerySection.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function toggleCardSelection(idx, isSelected) {
        const card = document.getElementById(`card-${idx}`);
        const cb = card ? card.querySelector(".card-checkbox") : null;
        if (isSelected) {
            state.selectedIndices.add(idx);
            if (card) card.classList.add("selected");
            if (cb) cb.checked = true;
        } else {
            state.selectedIndices.delete(idx);
            if (card) card.classList.remove("selected");
            if (cb) cb.checked = false;
        }
        updateSelectedCount();
    }

    function attachCardListeners() {
        document.querySelectorAll(".photo-card").forEach((card) => {
            const idx = parseInt(card.id.replace("card-", ""), 10);

            // Clicking anywhere on card toggles selection
            card.addEventListener("click", (e) => {
                // Ignore clicks originating from action buttons or checkbox directly
                if (e.target.closest("button") || e.target.classList.contains("card-checkbox")) {
                    return;
                }
                const isSelected = state.selectedIndices.has(idx);
                toggleCardSelection(idx, !isSelected);
            });

            // Double clicking opens fullscreen Lightbox
            card.addEventListener("dblclick", (e) => {
                if (e.target.closest("button")) return;
                openLightbox(idx);
            });
        });

        // Checkbox toggles
        document.querySelectorAll(".card-checkbox").forEach((cb) => {
            cb.addEventListener("change", (e) => {
                const idx = parseInt(cb.getAttribute("data-index"), 10);
                toggleCardSelection(idx, cb.checked);
            });
        });

        // View/Inspect single button
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

    // 8. Multi-Select & Batch Actions
    function selectAllPhotos() {
        state.selectedIndices = new Set(state.scrapedItems.map((_, i) => i));
        document.querySelectorAll(".card-checkbox").forEach((cb) => (cb.checked = true));
        document.querySelectorAll(".photo-card").forEach((c) => c.classList.add("selected"));
        updateSelectedCount();
    }

    function clearAllSelection() {
        state.selectedIndices.clear();
        document.querySelectorAll(".card-checkbox").forEach((cb) => (cb.checked = false));
        document.querySelectorAll(".photo-card").forEach((c) => c.classList.remove("selected"));
        updateSelectedCount();
    }

    elements.btnSelectAll.addEventListener("click", () => {
        const allSelected = state.selectedIndices.size === state.scrapedItems.length && state.scrapedItems.length > 0;
        if (allSelected) {
            clearAllSelection();
        } else {
            selectAllPhotos();
        }
    });

    // Floating Bottom Dock Shortcuts
    if (elements.btnDockSelectAll) {
        elements.btnDockSelectAll.addEventListener("click", selectAllPhotos);
    }

    if (elements.btnDockClearAll) {
        elements.btnDockClearAll.addEventListener("click", clearAllSelection);
    }

    if (elements.btnDockDownloadZip) {
        elements.btnDockDownloadZip.addEventListener("click", () => {
            if (elements.btnDownloadZip) elements.btnDownloadZip.click();
        });
    }

    if (elements.btnDockSaveLocal) {
        elements.btnDockSaveLocal.addEventListener("click", () => {
            if (elements.btnDownloadLocal) elements.btnDownloadLocal.click();
        });
    }

    function updateSelectedCount() {
        const count = state.selectedIndices.size;
        if (elements.selectedCount) elements.selectedCount.textContent = count;
        if (elements.selectedCountPicker) elements.selectedCountPicker.textContent = count;
        if (elements.selectedCountZip) elements.selectedCountZip.textContent = count;
        if (elements.selectedCountFiles) elements.selectedCountFiles.textContent = count;
        if (elements.dockSelectedCount) elements.dockSelectedCount.textContent = count;
        if (elements.dockCountZip) elements.dockCountZip.textContent = count;

        if (elements.btnChooseFolder) elements.btnChooseFolder.disabled = count === 0;
        if (elements.btnDownloadLocal) elements.btnDownloadLocal.disabled = count === 0;
        if (elements.btnDownloadZip) elements.btnDownloadZip.disabled = count === 0;
        if (elements.btnDownloadIndividual) elements.btnDownloadIndividual.disabled = count === 0;

        // Floating bottom dock visibility
        if (elements.floatingActionDock) {
            if (count >= 1 && !elements.gallerySection.classList.contains("hidden")) {
                elements.floatingActionDock.classList.remove("hidden");
            } else {
                elements.floatingActionDock.classList.add("hidden");
            }
        }

        if (elements.selectAllText) {
            elements.selectAllText.textContent =
                count === state.scrapedItems.length && count > 0 ? "Deselect All" : "Select All";
        }
    }

    // 9. Save Directly into User-Selected Local Folder (Native File System Access)
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
                        if (elements.folderGuideModal) elements.folderGuideModal.classList.remove("hidden");
                    }
                }
            } else {
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

    // 10. Download ZIP in Browser
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
                    post_id: state.currentPostId || "facebook_photos",
                    items: selectedItems,
                    folder_name: albumName || null,
                }),
            });

            if (!res.ok) throw new Error("ZIP generation failed on server.");

            const blob = await res.blob();
            const blobUrl = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.style.display = "none";
            a.href = blobUrl;
            a.download = `${albumName || `facebook_${state.currentPostId || "photos"}`}.zip`;
            document.body.appendChild(a);
            a.click();

            setTimeout(() => {
                a.remove();
                window.URL.revokeObjectURL(blobUrl);
            }, 2000);

            showToast(`ZIP Archive downloaded with ${selectedItems.length} photos!`, "success");
        } catch (err) {
            console.error("ZIP download error:", err);
            showToast("Failed to download ZIP archive.", "error");
        }
    });

    // 11. Download Individual Files
    elements.btnDownloadIndividual.addEventListener("click", async () => {
        const selectedItems = Array.from(state.selectedIndices).map((i) => state.scrapedItems[i]);
        if (selectedItems.length === 0) return;

        showToast(`Starting download of ${selectedItems.length} individual images...`, "info");
        for (let i = 0; i < selectedItems.length; i++) {
            const item = selectedItems[i];
            const ext = getExtensionFromUrl(item.url);
            const filename = item.suggested_filename || `photo_${String(i + 1).padStart(3, "0")}${ext}`;
            const downloadUrl = `/api/download-single?url=${encodeURIComponent(item.url)}&filename=${encodeURIComponent(filename)}`;

            const a = document.createElement("a");
            a.style.display = "none";
            a.href = downloadUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();

            await new Promise((r) => setTimeout(r, 400));
        }
        showToast(`Triggered ${selectedItems.length} browser file downloads!`, "success");
    });

    // 12. Save to Host Server Location
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

    // 13. Open Folder in Finder/Explorer
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

    // 14. Fullscreen Lightbox Modal
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
            item.width && item.height ? `${item.width} × ${item.height} px` : "Full Resolution";
        
        if (elements.lightboxMime) {
            const ext = (item.mime_type || "image/jpeg").split("/")[1]?.toUpperCase() || "JPG";
            elements.lightboxMime.textContent = ext;
        }
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

    // 15. Global Keyboard Shortcuts
    window.addEventListener("keydown", (e) => {
        // Lightbox controls
        if (!elements.lightboxModal.classList.contains("hidden")) {
            if (e.key === "Escape") closeLightbox();
            if (e.key === "ArrowLeft") elements.btnLightboxPrev.click();
            if (e.key === "ArrowRight") elements.btnLightboxNext.click();
            return;
        }

        // Health / Folder guide modal close on Escape
        if (!elements.healthModal.classList.contains("hidden") && e.key === "Escape") {
            elements.healthModal.classList.add("hidden");
            return;
        }
        if (elements.folderGuideModal && !elements.folderGuideModal.classList.contains("hidden") && e.key === "Escape") {
            elements.folderGuideModal.classList.add("hidden");
            return;
        }

        // Cmd/Ctrl + A selects all photos when gallery is displayed
        if ((e.metaKey || e.ctrlKey) && (e.key === "a" || e.key === "A")) {
            if (!elements.gallerySection.classList.contains("hidden") && state.scrapedItems.length > 0) {
                if (document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
                    e.preventDefault();
                    selectAllPhotos();
                }
            }
        }
    });

    // 16. System Health Modal
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

    // 17. Helper Animations & Stepper
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

            // Step progression & real-time log emissions
            if (seconds === 1) {
                activateStep(0);
                appendLog("[Playwright] Launching Chromium browser automation engine...", "playwright");
            }
            if (seconds === 2) {
                activateStep(1);
                appendLog("[Network] Navigating to Facebook post and bypassing consent/login dialogs...", "playwright");
            }
            if (seconds === 3) {
                appendLog("[GraphQL] Intercepting post payload & resolving attached photo IDs...", "scraper");
            }
            if (seconds === 4) {
                activateStep(2);
                appendLog("[Scraper] Expanding carousel collage & fetching uncompressed CDN assets...", "scraper");
            }
            if (seconds === 6) {
                activateStep(3);
                appendLog("[CDN] Traversing high-resolution photo nodes...", "scraper");
            }
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
            }, 3000);
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
