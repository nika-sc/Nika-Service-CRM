$(document).ready(function() {
    $('.nav-treeview .nav-link.active').each(function() {
        const parentItem = $(this).closest('.nav-treeview').closest('.nav-item');
        if (parentItem.length) {
            parentItem.addClass('menu-open');
            const icon = parentItem.find('.right');
            if (icon.length) {
                icon.removeClass('fa-angle-left').addClass('fa-angle-down');
            }
        }
    });

    $('.nav-treeview .nav-link').on('click', function() {
        const parentItem = $(this).closest('.nav-treeview').closest('.nav-item');
        if (parentItem.length) {
            parentItem.addClass('menu-open');
            const icon = parentItem.find('.right');
            if (icon.length) {
                icon.removeClass('fa-angle-left').addClass('fa-angle-down');
            }
        }
    });

    $('.mac-menu-item.dropdown').on('mouseenter', function() {
        if (window.innerWidth > 768) {
            $(this).addClass('show');
            $(this).find('.mac-dropdown-menu').addClass('show');
        }
    });

    $('.mac-menu-item.dropdown').on('mouseleave', function() {
        if (window.innerWidth > 768) {
            $(this).removeClass('show');
            $(this).find('.mac-dropdown-menu').removeClass('show');
        }
    });

    function closeMobileMenu() {
        const $drawer = $('#macMobileDrawer');
        $drawer.removeClass('open').attr('hidden', true);
        $('#macMobileOverlay').removeClass('show').attr('aria-hidden', 'true');
        $('body').removeClass('mobile-menu-open');
        $('#macMobileToggle').attr('aria-expanded', 'false');
        $('.mac-menu').removeClass('mobile-open');
        $('.mac-menu-item.dropdown').removeClass('show');
    }

    function openMobileMenu() {
        const $drawer = $('#macMobileDrawer');
        if (!$drawer.length) return;
        $drawer.removeAttr('hidden').addClass('open');
        $('#macMobileOverlay').addClass('show').attr('aria-hidden', 'false');
        $('body').addClass('mobile-menu-open');
        $('#macMobileToggle').attr('aria-expanded', 'true');
    }

    $('#macMobileToggle').on('click', function() {
        if ($('#macMobileDrawer').hasClass('open')) {
            closeMobileMenu();
        } else {
            openMobileMenu();
        }
    });
    $('#macMobileDrawerClose, #macMobileOverlay').on('click', closeMobileMenu);

    $(document).on('click', '.mac-mobile-drawer-link', function() {
        if (window.innerWidth <= 768) {
            closeMobileMenu();
        }
    });

    $('#staffChatMobileOpen').on('click', function() {
        closeMobileMenu();
        const fab = document.getElementById('staffChatFab');
        if (fab) fab.click();
    });

    $(window).on('resize', function() {
        if (window.innerWidth > 768) {
            closeMobileMenu();
        }
    });

    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
