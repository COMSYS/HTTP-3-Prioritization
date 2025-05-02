module.exports = {
  extends: 'lighthouse:default',
  settings: {
    formFactor: 'desktop',
    emulatedUserAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4590.2 Safari/537.36 Chrome-Lighthouse',
    throttlingMethod: "provided",
    onlyCategories: ["performance"],
    maxWaitForLoad: 45000,
    screenEmulation: {width: 1366, height: 768, deviceScaleFactor: 1, mobile: false, disabled: false},
  },
  passes: [{
    passName: 'defaultPass',
    pauseAfterFcpMs: 1000,
    pauseAfterLoadMs: 1000,
    networkQuietThresholdMs: 1000,
    cpuQuietThresholdMs: 1000,
  }],
};
