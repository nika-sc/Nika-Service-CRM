(function (w) {
    w.NIKA_LOCALE = w.NIKA_LOCALE || { phonePrefix: "7", moneySymbol: "₽", phonePrefixPlus: "+7" };

    function phonePrefix() {
        var p = String((w.NIKA_LOCALE && w.NIKA_LOCALE.phonePrefix) || "7").replace(/\D/g, "");
        return p || "7";
    }

    w.nikaPhonePrefix = phonePrefix;
    w.nikaMoneySymbol = function () {
        return (w.NIKA_LOCALE && w.NIKA_LOCALE.moneySymbol) || "₽";
    };
    w.nikaPhoneDefaultValue = function () {
        return "+" + phonePrefix();
    };

    w.nikaNormalizePhone = function (value) {
        var d = String(value || "").replace(/\D/g, "");
        if (d.indexOf("00") === 0) d = d.slice(2);
        var prefix = phonePrefix();
        if (prefix === "7") {
            if (d.length === 12 && "78".indexOf(d.charAt(0)) !== -1 && "78".indexOf(d.charAt(1)) !== -1 && d.charAt(2) === "9") {
                d = "7" + d.slice(2);
            }
            if (d.charAt(0) === "8") d = "7" + d.slice(1);
            if (d && d.charAt(0) !== "7") d = "7" + d;
            return d;
        }
        if (d.charAt(0) === "0") d = d.replace(/^0+/, "");
        var localLen = 9;
        if (d.indexOf(prefix) === 0) return d.slice(0, prefix.length + localLen);
        return (prefix + d).slice(0, prefix.length + localLen);
    };

    w.nikaFormatPhoneDisplay = function (value) {
        var digits = w.nikaNormalizePhone(value);
        var prefix = phonePrefix();
        if (prefix === "7" && digits.length === 11 && digits.charAt(0) === "7") {
            return "+" + digits.charAt(0) + "(" + digits.slice(1, 4) + ")" + digits.slice(4, 7) + "-" + digits.slice(7, 9) + "-" + digits.slice(9);
        }
        if (digits.indexOf(prefix) === 0) {
            var rest = digits.slice(prefix.length);
            if (prefix === "996" && rest.length === 9) {
                return "+" + prefix + " " + rest.slice(0, 3) + " " + rest.slice(3, 6) + " " + rest.slice(6, 9);
            }
            return "+" + digits;
        }
        return value;
    };

    w.nikaMaskPhoneInput = function (value) {
        var prefix = phonePrefix();
        var digits = w.nikaNormalizePhone(value);
        if (!digits) return "";
        if (prefix === "7") {
            var masked = "+";
            masked += digits.charAt(0) || "";
            if (digits.length > 1) masked += "(" + digits.slice(1, 4);
            if (digits.length >= 4) masked += ")";
            if (digits.length >= 5) masked += digits.slice(4, 7);
            if (digits.length >= 7) masked += "-" + digits.slice(7, 9);
            if (digits.length >= 9) masked += "-" + digits.slice(9, 11);
            return masked;
        }
        var rest = digits.indexOf(prefix) === 0 ? digits.slice(prefix.length) : digits;
        rest = rest.slice(0, 9);
        var out = "+" + prefix;
        if (rest.length) out += " " + rest.slice(0, 3);
        if (rest.length > 3) out += " " + rest.slice(3, 6);
        if (rest.length > 6) out += " " + rest.slice(6, 9);
        return out;
    };
})(window);
