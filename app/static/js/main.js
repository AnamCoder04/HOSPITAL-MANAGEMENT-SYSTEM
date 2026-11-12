/* ==========================================================================
   MediCare HMS - small, dependency-free helpers.
   Bootstrap's own JS bundle handles modals, dropdowns, collapse and alerts.
   ========================================================================== */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    /* 1. Add a shadow to the public navbar once the page is scrolled. */
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

    /* 3. Close the public mobile menu after clicking a link inside it. */
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

    /* 4. Dashboard sidebar: slide-in drawer below 992px. */
    var sidebar = document.getElementById("hmsSidebar");
    var backdrop = document.querySelector("[data-sidebar-backdrop]");
    var toggles = document.querySelectorAll("[data-sidebar-toggle]");
    var closers = document.querySelectorAll("[data-sidebar-close]");

    var isDesktop = function () {
      return window.matchMedia("(min-width: 992px)").matches;
    };

    var openSidebar = function () {
      if (!sidebar) return;
      sidebar.classList.add("is-open");
      document.body.classList.add("sidebar-open");
      if (backdrop) {
        backdrop.hidden = false;
        backdrop.classList.add("is-visible");
      }
      toggles.forEach(function (btn) {
        btn.setAttribute("aria-expanded", "true");
      });
    };

    var closeSidebar = function () {
      if (!sidebar) return;
      sidebar.classList.remove("is-open");
      document.body.classList.remove("sidebar-open");
      if (backdrop) {
        backdrop.classList.remove("is-visible");
        backdrop.hidden = true;
      }
      toggles.forEach(function (btn) {
        btn.setAttribute("aria-expanded", "false");
      });
    };

    toggles.forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (sidebar && sidebar.classList.contains("is-open")) {
          closeSidebar();
        } else {
          openSidebar();
        }
      });
    });

    closers.forEach(function (btn) {
      btn.addEventListener("click", closeSidebar);
    });

    if (backdrop) {
      backdrop.addEventListener("click", closeSidebar);
    }

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeSidebar();
    });

    window.addEventListener("resize", function () {
      if (isDesktop()) closeSidebar();
    });
  });
})();
