/**
 * Tutorial Page - Interactive URL Inspector & Step-by-Step Guide
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide Icons
    if (window.lucide) {
        lucide.createIcons();
    }

    // Elements
    const testerUrlInput = document.getElementById('testerUrlInput');
    const btnTesterAnalyze = document.getElementById('btnTesterAnalyze');
    const testerResultBox = document.getElementById('testerResultBox');
    const resultStatusIcon = document.getElementById('resultStatusIcon');
    const resultTitle = document.getElementById('resultTitle');
    const resultDescription = document.getElementById('resultDescription');
    const detailLinkType = document.getElementById('detailLinkType');
    const detailExtractedId = document.getElementById('detailExtractedId');
    const detailAlbumSupport = document.getElementById('detailAlbumSupport');
    const btnUseInDownloader = document.getElementById('btnUseInDownloader');

    // Toast Container
    const toastContainer = document.getElementById('toastContainer');

    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let iconName = 'info';
        if (type === 'success') iconName = 'check-circle';
        if (type === 'error') iconName = 'alert-circle';
        
        toast.innerHTML = `
            <i data-lucide="${iconName}"></i>
            <span>${message}</span>
        `;
        
        toastContainer.appendChild(toast);
        if (window.lucide) lucide.createIcons();
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // URL Inspector Logic
    function analyzeUrl(rawUrl) {
        const url = (rawUrl || '').trim();
        if (!url) {
            testerResultBox.classList.add('hidden');
            return;
        }

        testerResultBox.classList.remove('hidden');

        try {
            const parsed = new URL(url);
            const host = parsed.hostname.toLowerCase();
            const path = parsed.pathname;
            const search = parsed.search;

            const isFb = host.includes('facebook.com') || host.includes('fb.com') || host.includes('fb.watch');
            if (!isFb) {
                renderResult({
                    valid: false,
                    title: 'Non-Facebook URL',
                    desc: 'The provided URL does not belong to facebook.com or fb.com.',
                    type: 'External Domain',
                    id: 'N/A',
                    album: 'Unsupported'
                });
                return;
            }

            // Check for profile homepage without post
            if (path === '/' || path === '' || (!path.includes('/') && !search)) {
                renderResult({
                    valid: false,
                    title: 'Facebook Homepage / Domain Only',
                    desc: 'This is the Facebook root URL. Please navigate to a specific post or album.',
                    type: 'Root Domain',
                    id: 'N/A',
                    album: 'Unsupported'
                });
                return;
            }

            // Check if profile URL only
            const pathSegments = path.split('/').filter(Boolean);
            if (pathSegments.length === 1 && !search && !pathSegments[0].includes('share') && !pathSegments[0].includes('photo')) {
                renderResult({
                    valid: false,
                    title: 'User / Page Profile URL',
                    desc: 'This is a timeline or profile URL. Click on the post timestamp to get the direct post permalink.',
                    type: 'Profile Timeline',
                    id: pathSegments[0],
                    album: 'Unsupported'
                });
                return;
            }

            // 1. Share Links (fb.com/share/p/...)
            if (path.includes('/share/p/') || path.includes('/share/v/') || path.includes('/share/r/')) {
                const match = path.match(/\/share\/[pvr]\/([a-zA-Z0-9_-]+)/);
                const shareId = match ? match[1] : 'share_link';
                renderResult({
                    valid: true,
                    title: 'Valid Mobile Share Link',
                    desc: 'Clean mobile share link. FB Downloader PRO will automatically resolve the full album and bypass login prompts.',
                    type: 'Mobile Share Permalink',
                    id: shareId,
                    album: 'Full Album Supported (200+ Photos)',
                    url: url
                });
                return;
            }

            // 2. Standard Posts (posts/pfbid... or posts/12345)
            if (path.includes('/posts/')) {
                const match = path.match(/\/posts\/([a-zA-Z0-9_-]+)/);
                const postId = match ? match[1] : 'post_id';
                renderResult({
                    valid: true,
                    title: 'Valid Desktop Post Permalink',
                    desc: 'Standard Facebook post link. Scraper will extract all attached photos and resolve hidden collage items.',
                    type: 'Desktop Post Permalink',
                    id: postId,
                    album: 'Multi-Photo Grid Supported',
                    url: url
                });
                return;
            }

            // 3. Album Set (media/set/?set=...)
            if (path.includes('/media/set') || search.includes('set=')) {
                const params = new URLSearchParams(search);
                const setId = params.get('set') || 'album_set';
                renderResult({
                    valid: true,
                    title: 'Direct Media Album Collection',
                    desc: 'Direct Facebook album collection batch. Traverses all photos via deep carousel viewer.',
                    type: 'Media Album Set',
                    id: setId,
                    album: 'Deep Album Supported (200+ Photos)',
                    url: url
                });
                return;
            }

            // 4. Photo Theater (photo/?fbid=...)
            if (path.includes('/photo') || search.includes('fbid=')) {
                const params = new URLSearchParams(search);
                const fbid = params.get('fbid') || 'photo_id';
                renderResult({
                    valid: true,
                    title: 'Direct Photo Theater Link',
                    desc: 'Photo theater view. Scraper will download this photo and step through the surrounding album collection.',
                    type: 'Photo Theater View',
                    id: fbid,
                    album: 'Carousel Supported',
                    url: url
                });
                return;
            }

            // 5. Permalink (permalink.php?story_fbid=...)
            if (path.includes('/permalink.php') || search.includes('story_fbid=')) {
                const params = new URLSearchParams(search);
                const fbid = params.get('story_fbid') || 'story_fbid';
                renderResult({
                    valid: true,
                    title: 'Facebook Story Permalink',
                    desc: 'Valid story permalink. Scraper will load and resolve all media attached to this story.',
                    type: 'Story Permalink',
                    id: fbid,
                    album: 'Supported',
                    url: url
                });
                return;
            }

            // Fallback generic valid FB link
            renderResult({
                valid: true,
                title: 'Recognized Facebook Link',
                desc: 'This URL appears to be a valid Facebook link. The engine will inspect and extract attached media.',
                type: 'Generic Facebook URL',
                id: 'Auto-detected',
                album: 'Auto-detected',
                url: url
            });

        } catch (e) {
            renderResult({
                valid: false,
                title: 'Invalid URL Format',
                desc: 'Please enter a valid URL starting with https://www.facebook.com/...',
                type: 'Malformed URL',
                id: 'N/A',
                album: 'N/A'
            });
        }
    }

    function renderResult(data) {
        if (data.valid) {
            resultStatusIcon.className = 'result-status-icon valid';
            resultStatusIcon.innerHTML = '<i data-lucide="check-circle-2"></i>';
            resultTitle.textContent = data.title;
            resultTitle.style.color = 'var(--accent-emerald)';
            resultDescription.textContent = data.desc;
            detailLinkType.textContent = data.type;
            detailLinkType.className = 'detail-value highlight';
            detailExtractedId.textContent = data.id;
            detailAlbumSupport.textContent = data.album;
            detailAlbumSupport.className = 'detail-value text-emerald';
            btnUseInDownloader.style.display = 'inline-flex';
            btnUseInDownloader.onclick = () => {
                window.location.href = `/?url=${encodeURIComponent(data.url)}`;
            };
        } else {
            resultStatusIcon.className = 'result-status-icon invalid';
            resultStatusIcon.innerHTML = '<i data-lucide="alert-circle"></i>';
            resultTitle.textContent = data.title;
            resultTitle.style.color = 'var(--accent-rose)';
            resultDescription.textContent = data.desc;
            detailLinkType.textContent = data.type;
            detailLinkType.className = 'detail-value text-muted';
            detailExtractedId.textContent = data.id;
            detailAlbumSupport.textContent = data.album;
            detailAlbumSupport.className = 'detail-value text-muted';
            btnUseInDownloader.style.display = 'none';
        }

        if (window.lucide) lucide.createIcons();
    }

    // Event Listeners for Tester
    btnTesterAnalyze.addEventListener('click', () => {
        analyzeUrl(testerUrlInput.value);
    });

    testerUrlInput.addEventListener('input', () => {
        analyzeUrl(testerUrlInput.value);
    });

    testerUrlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            analyzeUrl(testerUrlInput.value);
        }
    });

    // Device Tabs Switcher
    const tabPills = document.querySelectorAll('.tab-pill');
    const tabContents = document.querySelectorAll('.tab-content');

    tabPills.forEach(pill => {
        pill.addEventListener('click', () => {
            tabPills.forEach(p => p.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            pill.classList.add('active');
            const targetId = pill.getAttribute('data-tab');
            const targetContent = document.getElementById(targetId);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });

    // 1-Click Copy Sample Buttons
    document.querySelectorAll('.btn-copy-sample').forEach(btn => {
        btn.addEventListener('click', async () => {
            const sampleUrl = btn.getAttribute('data-url');
            if (sampleUrl) {
                try {
                    await navigator.clipboard.writeText(sampleUrl);
                    showToast('Sample link copied to clipboard!', 'success');
                    testerUrlInput.value = sampleUrl;
                    analyzeUrl(sampleUrl);
                } catch (err) {
                    testerUrlInput.value = sampleUrl;
                    analyzeUrl(sampleUrl);
                    showToast('Loaded sample into URL Inspector!', 'info');
                }
            }
        });
    });

    // Pre-populate tester if url in query params
    const params = new URLSearchParams(window.location.search);
    const testParam = params.get('url');
    if (testParam) {
        testerUrlInput.value = testParam;
        analyzeUrl(testParam);
    }
});
