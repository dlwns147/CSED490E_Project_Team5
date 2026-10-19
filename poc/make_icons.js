// Icons for the slides (figs/icons/*.png), rendered once from react-icons; the slide script only reads the PNG files.
// usage: npm install react@18.3.1 react-dom@18.3.1 react-icons@5.3.0 sharp@0.33.5 && node poc/make_icons.js
const path = require("path");
const fs = require("fs");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const bs = require("react-icons/bs");

const OUT = path.join(__dirname, "..", "figs", "icons");
const ICONS = {   // name: [component, colour]
  robot: [fa.FaRobot, "#4472C4"], coins: [fa.FaCoins, "#ED7D31"], gpu: [bs.BsGpuCard, "#44546A"],
  fact: [fa.FaFileAlt, "#38761D"], check: [fa.FaCheckCircle, "#38761D"], brain: [fa.FaBrain, "#C00000"],
  page: [fa.FaFileAlt, "#A5A5A5"], pagehot: [fa.FaFileAlt, "#ED7D31"], warn: [fa.FaExclamationTriangle, "#C00000"],
};
fs.mkdirSync(OUT, { recursive: true });
(async () => {
  for (const [name, [Icon, color]] of Object.entries(ICONS)) {
    const svg = renderToStaticMarkup(React.createElement(Icon, { color, size: 256 }));
    await sharp(Buffer.from(svg)).png().toFile(path.join(OUT, name + ".png"));
    console.log("wrote figs/icons/" + name + ".png");
  }
})();
