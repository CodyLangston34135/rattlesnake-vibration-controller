// Populate the sidebar
//
// This is a script, and not included directly in the page, to control the total size of the book.
// The TOC contains an entry for each page, so if each page includes a copy of the TOC,
// the total size of the page becomes O(n**2).
class MDBookSidebarScrollbox extends HTMLElement {
    constructor() {
        super();
    }
    connectedCallback() {
        this.innerHTML = '<ol class="chapter"><li class="chapter-item expanded affix "><a href="abstract.html">Abstract</a></li><li class="chapter-item expanded affix "><a href="nomenclature.html">Nomenclature</a></li><li class="chapter-item expanded affix "><a href="notation.html">Notation</a></li><li class="chapter-item expanded "><a href="chapter_01.html"><strong aria-hidden="true">1.</strong> Introduction</a></li><li class="chapter-item expanded affix "><li class="spacer"></li><li class="chapter-item expanded affix "><li class="part-title">Part I. Rattlesnake Overview</li><li class="chapter-item expanded "><a href="chapter_02.html"><strong aria-hidden="true">2.</strong> Acquiring and Running Rattlesnake</a></li><li class="chapter-item expanded "><a href="chapter_03.html"><strong aria-hidden="true">3.</strong> Using Rattlesnake</a></li><li class="chapter-item expanded affix "><li class="spacer"></li><li class="chapter-item expanded affix "><li class="part-title">Part II. Rattlesnake Hardware Devices</li><li class="chapter-item expanded "><a href="chapter_04.html"><strong aria-hidden="true">4.</strong> NI-DAQMX Devices</a></li><li class="chapter-item expanded "><a href="chapter_05.html"><strong aria-hidden="true">5.</strong> LAN-XI Devices</a></li><li class="chapter-item expanded "><a href="chapter_06.html"><strong aria-hidden="true">6.</strong> Data Physics Quattro Devices</a></li><li class="chapter-item expanded "><a href="chapter_07.html"><strong aria-hidden="true">7.</strong> Data Physics 900-series Devices</a></li><li class="chapter-item expanded "><a href="chapter_08.html"><strong aria-hidden="true">8.</strong> Virtual Control using State Space Matrices</a></li><li class="chapter-item expanded "><a href="chapter_09.html"><strong aria-hidden="true">9.</strong> Virtual Control using Finite Element Results in Exodus Files</a></li><li class="chapter-item expanded "><a href="chapter_10.html"><strong aria-hidden="true">10.</strong> Virtual Control using SDYNPY System Objects</a></li><li class="chapter-item expanded "><a href="chapter_11.html"><strong aria-hidden="true">11.</strong> Implementing New Hardward Devices with Rattlesnake</a></li><li class="chapter-item expanded affix "><li class="spacer"></li><li class="chapter-item expanded affix "><li class="part-title">Part III. Rattlesnake Environments</li><li class="chapter-item expanded "><a href="chapter_12.html"><strong aria-hidden="true">12.</strong> Multiple Input/Multiple Ouptut Random Vibration</a></li><li class="chapter-item expanded "><a href="chapter_13.html"><strong aria-hidden="true">13.</strong> Multiple Input/Multiple Output Transient Control</a></li><li class="chapter-item expanded "><a href="chapter_14.html"><strong aria-hidden="true">14.</strong> Time History Generator</a></li><li class="chapter-item expanded "><a href="chapter_15.html"><strong aria-hidden="true">15.</strong> Modal Testing</a></li><li class="chapter-item expanded "><a href="chapter_16.html"><strong aria-hidden="true">16.</strong> Combined Environments</a></li><li class="chapter-item expanded "><a href="chapter_17.html"><strong aria-hidden="true">17.</strong> Implementing New Environment Types</a></li><li class="chapter-item expanded affix "><li class="spacer"></li><li class="chapter-item expanded affix "><a href="appendix_a.html">Appendix A. Introduction to Example Problems</a></li><li class="chapter-item expanded affix "><a href="appendix_b.html">Appendix B. Example Problem using NI cDAQ Hardware and the NII DAQmx Interface</a></li><li class="chapter-item expanded affix "><a href="appendix_c.html">Appendix C. Synthetic Example Problem with a SDynPy System</a></li><li class="chapter-item expanded affix "><a href="appendix_d.html">Appendix D. Synthetic Example Problem using State Space Metrics</a></li><li class="chapter-item expanded affix "><li class="spacer"></li><li class="chapter-item expanded affix "><a href="contributors.html">Contributors </a></li></ol>';
        // Set the current, active page, and reveal it if it's hidden
        let current_page = document.location.href.toString().split("#")[0].split("?")[0];
        if (current_page.endsWith("/")) {
            current_page += "index.html";
        }
        var links = Array.prototype.slice.call(this.querySelectorAll("a"));
        var l = links.length;
        for (var i = 0; i < l; ++i) {
            var link = links[i];
            var href = link.getAttribute("href");
            if (href && !href.startsWith("#") && !/^(?:[a-z+]+:)?\/\//.test(href)) {
                link.href = path_to_root + href;
            }
            // The "index" page is supposed to alias the first chapter in the book.
            if (link.href === current_page || (i === 0 && path_to_root === "" && current_page.endsWith("/index.html"))) {
                link.classList.add("active");
                var parent = link.parentElement;
                if (parent && parent.classList.contains("chapter-item")) {
                    parent.classList.add("expanded");
                }
                while (parent) {
                    if (parent.tagName === "LI" && parent.previousElementSibling) {
                        if (parent.previousElementSibling.classList.contains("chapter-item")) {
                            parent.previousElementSibling.classList.add("expanded");
                        }
                    }
                    parent = parent.parentElement;
                }
            }
        }
        // Track and set sidebar scroll position
        this.addEventListener('click', function(e) {
            if (e.target.tagName === 'A') {
                sessionStorage.setItem('sidebar-scroll', this.scrollTop);
            }
        }, { passive: true });
        var sidebarScrollTop = sessionStorage.getItem('sidebar-scroll');
        sessionStorage.removeItem('sidebar-scroll');
        if (sidebarScrollTop) {
            // preserve sidebar scroll position when navigating via links within sidebar
            this.scrollTop = sidebarScrollTop;
        } else {
            // scroll sidebar to current active section when navigating via "next/previous chapter" buttons
            var activeSection = document.querySelector('#sidebar .active');
            if (activeSection) {
                activeSection.scrollIntoView({ block: 'center' });
            }
        }
        // Toggle buttons
        var sidebarAnchorToggles = document.querySelectorAll('#sidebar a.toggle');
        function toggleSection(ev) {
            ev.currentTarget.parentElement.classList.toggle('expanded');
        }
        Array.from(sidebarAnchorToggles).forEach(function (el) {
            el.addEventListener('click', toggleSection);
        });
    }
}
window.customElements.define("mdbook-sidebar-scrollbox", MDBookSidebarScrollbox);
