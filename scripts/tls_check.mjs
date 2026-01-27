const url = process.argv[2];
if (!url) {
  console.error('usage: node scripts/tls_check.mjs "<url>"');
  process.exit(2);
}

(async () => {
  try {
    const res = await fetch(url, { redirect: "follow" });
    console.log("status:", res.status);
    console.log("content-type:", res.headers.get("content-type"));
    const text = await res.text();
    console.log("body head:", text.slice(0, 300));
  } catch (e) {
    console.error("FAILED:", e);
    process.exit(1);
  }
})();







