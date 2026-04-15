// Period filter (reports): quick buttons + custom date range
(function () {
  if (window.__periodFilterInitialized) return;
  window.__periodFilterInitialized = true;

  function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  // Все периоды заканчиваются сегодня (to = today), кроме «Вчера», «Позавчера», «Прошлый месяц»
  function calculatePeriod(period) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    let from = new Date(today);
    let to = new Date(today);

    switch (period) {
      case "today":
        break;
      case "yesterday":
        from.setDate(from.getDate() - 1);
        to.setDate(to.getDate() - 1);
        break;
      case "day-before":
        from.setDate(from.getDate() - 2);
        to.setDate(to.getDate() - 2);
        break;
      case "last-7-days":
        from.setDate(from.getDate() - 6);
        break;
      case "last-30-days":
        from.setDate(from.getDate() - 29);
        break;
      case "week": {
        // Начало недели (понедельник) — по сегодня
        const dayOfWeek = from.getDay();
        const diff = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
        from.setDate(from.getDate() - diff);
        break;
      }
      case "month":
        // Текущий месяц: с 1-го числа по сегодня
        from.setDate(1);
        break;
      case "quarter":
        // Квартал: последние ~3 месяца по сегодня
        from.setDate(from.getDate() - 89);
        break;
      case "half-year":
        // Полгода: последние ~6 месяцев по сегодня
        from.setDate(from.getDate() - 182);
        break;
      case "last-month":
        from.setMonth(from.getMonth() - 1);
        from.setDate(1);
        to.setDate(0); // Последний день прошлого месяца
        break;
      case "year":
      case "year-to-date":
        // Год / с начала года: 1 января — сегодня
        from.setMonth(0);
        from.setDate(1);
        break;
    }

    return {
      from: formatDate(from),
      to: formatDate(to),
    };
  }

  function highlightActivePeriod(fromValue, toValue, buttons) {
    if (!fromValue || !toValue) return;

    const periods = [
      "today",
      "yesterday",
      "day-before",
      "last-7-days",
      "last-30-days",
      "week",
      "month",
      "quarter",
      "half-year",
      "last-month",
      "year",
      "year-to-date",
    ];

    for (const period of periods) {
      const dates = calculatePeriod(period);
      if (dates.from === fromValue && dates.to === toValue) {
        buttons.forEach((btn) => {
          if (btn.dataset.period === period) btn.classList.add("active");
        });
        break;
      }
    }
  }

  function initPeriodFilter() {
    const periodBtns = document.querySelectorAll(".period-btn");
    const dateFrom = document.getElementById("periodDateFrom");
    const dateTo = document.getElementById("periodDateTo");

    if (!dateFrom || !dateTo || !periodBtns.length) return;

    periodBtns.forEach((btn) => {
      btn.addEventListener("click", function () {
        const period = this.dataset.period;
        const dates = calculatePeriod(period);

        dateFrom.value = dates.from;
        dateTo.value = dates.to;

        periodBtns.forEach((b) => b.classList.remove("active"));
        this.classList.add("active");

        const form = this.closest("form");
        if (form) form.submit();
      });
    });

    highlightActivePeriod(dateFrom.value, dateTo.value, periodBtns);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPeriodFilter);
  } else {
    initPeriodFilter();
  }
})();

