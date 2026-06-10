const fs = require("fs");
const path = require("path");

const DOMAIN = "https://umitsural.com";
const ROOT = __dirname;

const files = fs
  .readdirSync(ROOT)
  .filter(file => file.endsWith(".html"))
  .filter(file => !file.startsWith("_"));

const urls = files.map(file => {
  const loc = file === "index.html"
    ? `${DOMAIN}/`
    : `${DOMAIN}/${file}`;

  return `  <url>
    <loc>${loc}</loc>
  </url>`;
});

const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.join("\n")}
</urlset>
`;

fs.writeFileSync(path.join(ROOT, "sitemap.xml"), sitemap);

console.log(`sitemap.xml created with ${files.length} pages.`);