/* ==========================================================================
   MediCare HMS - small, dependency-free helpers.
   Bootstrap's own JS bundle handles dropdowns, collapse and alerts.
   ========================================================================== */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    /* 1. Add a shadow to the navbar once the page is scrolled. */
    var navbar = document.getElementById("siteNavbar");
    if (navbar) {
      var onScroll = function () {
        navbar.classList.toggle("is-stuck", window.scrollY > 8);
      };
      onScroll();
      window.addEventListener("scroll", onScroll, { passive: true });
    }

    /* 2. Auto-dismiss flash messages after 5 seconds. */
    document.querySelectorAll(".flash-stack .alert").forEach(function (alertEl) {
      window.setTimeout(function () {
        if (window.bootstrap && window.bootstrap.Alert) {
          window.bootstrap.Alert.getOrCreateInstance(alertEl).close();
        }
      }, 5000);
    });

    /* 3. Close the mobile menu after clicking a link inside it. */
    var collapseEl = document.getElementById("publicNav");
    if (collapseEl) {
      collapseEl.querySelectorAll("a").forEach(function (link) {
        link.addEventListener("click", function () {
          if (collapseEl.classList.contains("show") && window.bootstrap) {
            window.bootstrap.Collapse.getOrCreateInstance(collapseEl).hide();
          }
        });
      });
    }
  });
})();
