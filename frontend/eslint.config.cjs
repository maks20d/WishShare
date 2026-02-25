const nextCoreWebVitals = require("eslint-config-next/core-web-vitals");

module.exports = [
  ...(Array.isArray(nextCoreWebVitals) ? nextCoreWebVitals : [nextCoreWebVitals]),
  {
    ignores: [".next/**", ".next-dev/**", "out/**", "build/**", "coverage/**"],
  },
];
