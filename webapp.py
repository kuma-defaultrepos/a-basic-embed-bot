import json
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request, send_file

APP = Flask(__name__)
DEFAULT_FILE = "embed_config.json"


def safe_json_path(name: str) -> Path:
    base = Path(name).name or DEFAULT_FILE
    if not base.lower().endswith(".json"):
        base = f"{base}.json"
    return Path(base)

HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Discord Embed Creator</title>
  <style>
    :root {
      --bg: radial-gradient(circle at 20% 20%, #122240 0, #0b1020 45%, #060914 100%);
      --panel: rgba(26, 34, 56, 0.8);
      --border: #334155;
      --accent: #60a5fa;
      --muted: #94a3b8;
      --text: #e2e8f0;
      --surface: #0f172a;
    }
    * { box-sizing: border-box; }
    body { font-family: "Inter", "Segoe UI", "SF Pro Text", sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 0; }
    .wrap { max-width: 960px; margin: 0 auto; padding: 28px; }
    h1 { margin-bottom: 8px; letter-spacing: 0.02em; }
    p.lead { color: var(--muted); margin-top: 0; }
    .card { background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 16px; margin-bottom: 16px; backdrop-filter: blur(6px); }
    label { display: block; margin: 8px 0 4px; }
    input, textarea { width: 100%; border: 1px solid var(--border); border-radius: 8px; padding: 10px; background: #0b1220; color: var(--text); }
    textarea { min-height: 80px; }
    button { background: var(--accent); color: white; border: none; border-radius: 10px; padding: 10px 16px; cursor: pointer; font-weight: 600; box-shadow: 0 10px 30px rgba(96,165,250,0.25); }
    button.secondary { background: #475569; box-shadow: none; }
    .fields { margin-top: 8px; }
    .field-row { display: grid; grid-template-columns: 1fr 1fr 90px 40px; gap: 8px; align-items: center; margin-bottom: 8px; }
    .status { margin-top: 8px; display: inline-block; }
    .preview-card { background: #0b0f1a; border: 1px solid #1f2937; border-radius: 12px; padding: 12px; }
    #preview { display: flex; justify-content: center; }
    .embed-shell { border-radius: 8px; background: #0b0f1a; padding: 8px; border: 1px solid #1f2937; width: min(680px, 100%); }
    .embed-card { display: grid; grid-template-columns: 4px 1fr; gap: 12px; background: #111827; border: 1px solid #1f2937; border-radius: 6px; padding: 12px; width: 100%; }
    .embed-color { width: 4px; border-radius: 3px; }
    .embed-body { display: flex; flex-direction: column; gap: 8px; }
    .embed-author { display: flex; gap: 8px; align-items: center; font-weight: 600; color: #cbd5e1; line-height: 1.2; }
    .embed-title { font-size: 16px; font-weight: 700; color: #e5e7eb; margin: 0; line-height: 1.3; overflow-wrap: anywhere; word-break: break-word; }
    .embed-desc { white-space: pre-line; color: #e5e7eb; line-height: 1.4; overflow-wrap: anywhere; word-break: break-word; }
    .embed-fields { display: flex; flex-wrap: wrap; gap: 8px; }
    .embed-field { flex: 1 1 100%; border: 1px solid #1f2937; border-radius: 4px; padding: 8px; background: #0f172a; }
    .embed-field.inline { flex: 1 1 calc(50% - 8px); min-width: 220px; }
    .embed-field-name { font-weight: 700; color: #e5e7eb; font-size: 13px; margin-bottom: 4px; }
    .embed-field-value { white-space: pre-line; color: #cbd5e1; font-size: 13px; line-height: 1.35; overflow-wrap: anywhere; word-break: break-word; }
    .embed-image { max-width: 100%; border-radius: 6px; margin-top: 8px; border: 1px solid #1f2937; }
    .thumb { width: 40px; height: 40px; border-radius: 6px; object-fit: cover; }
    .footer { color: #94a3b8; font-size: 12px; margin-top: 4px; }
    @media (min-width: 860px) {
      .embed-field.inline { flex: 1 1 calc(33% - 8px); }
    }
    .message-content { white-space: pre-wrap; color: #e5e7eb; margin-bottom: 8px; }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Discord Embed Creator</h1>
    <p class="lead">Build embeds, download the JSON, then upload it to the bot with <code>/embed import_file</code> (or drop it into your bot host).</p>

    <div class="card">
      <label>Message content</label>
      <textarea id="content" placeholder="Optional message text"></textarea>
    </div>

    <div class="card">
      <div style="display:flex; justify-content: space-between; align-items: center;">
        <h3 style="margin:0;">Embeds</h3>
        <button type="button" onclick="addEmbed()">+ Add embed</button>
      </div>
      <div id="embeds"></div>
    </div>

    <div class="card">
      <button onclick="downloadCurrent()">Download JSON</button>
      <label style="margin-left:12px;">File name <input type="text" id="fileName" value="embed_export.json" style="margin-left:6px; width:200px;" /></label>
      <label style="margin-left:12px;">Upload JSON <input type="file" id="upload" accept="application/json" style="margin-left:6px;" /></label>
      <span class="status" id="status"></span>
    </div>

    <div class="card preview-card">
      <h3 style="margin-top:0;">Live preview</h3>
      <div id="preview"></div>
    </div>
  </div>

  <script>
    function createEmbed() {
      return {
        title: "",
        description: "",
        color: "#5865F2",
        thumbnail: "",
        image: "",
        footer: "",
        author: { name: "", icon_url: "" },
        fields: [],
        collapsed: false,
      };
    }

    let fileName = "embed_export.json";
    let embeds = [createEmbed()];

    function addEmbed() {
      embeds.push(createEmbed());
      renderEmbeds();
    }

    function removeEmbed(idx) {
      embeds.splice(idx, 1);
      if (!embeds.length) embeds.push(createEmbed());
      renderEmbeds();
    }

    function addField(idx) {
      embeds[idx].fields.push({ name: "", value: "", inline: false });
      renderEmbeds();
    }

    function renderFields(idx, container) {
      const fields = embeds[idx].fields;
      container.innerHTML = "";
      fields.forEach((f, i) => {
        const row = document.createElement("div");
        row.className = "field-row";

        const name = document.createElement("input");
        name.placeholder = "Name";
        name.value = f.name || "";
        name.oninput = (e) => { f.name = e.target.value; renderPreview(); };

        const value = document.createElement("input");
        value.placeholder = "Value";
        value.value = f.value || "";
        value.oninput = (e) => { f.value = e.target.value; renderPreview(); };

        const inline = document.createElement("input");
        inline.type = "checkbox";
        inline.checked = f.inline || false;
        inline.onchange = (e) => { f.inline = e.target.checked; renderPreview(); };

        const remove = document.createElement("button");
        remove.className = "secondary";
        remove.innerText = "X";
        remove.type = "button";
        remove.onclick = () => { fields.splice(i, 1); renderEmbeds(); };

        const inlineLabel = document.createElement("label");
        inlineLabel.style.display = "flex";
        inlineLabel.style.alignItems = "center";
        inlineLabel.appendChild(inline);
        inlineLabel.appendChild(document.createTextNode(" inline"));

        row.appendChild(name);
        row.appendChild(value);
        row.appendChild(inlineLabel);
        row.appendChild(remove);
        container.appendChild(row);
      });
    }

    function renderEmbeds() {
      const container = document.getElementById("embeds");
      container.innerHTML = "";
      embeds.forEach((emb, idx) => {
        const card = document.createElement("div");
        card.className = "card";

        const header = document.createElement("div");
        header.style.display = "flex";
        header.style.justifyContent = "space-between";
        header.style.alignItems = "center";
        const title = document.createElement("h4");
        title.style.margin = "0";
        title.textContent = `Embed #${idx + 1}`;
        const controls = document.createElement("div");
        controls.style.display = "flex";
        controls.style.gap = "8px";

        const collapseBtn = document.createElement("button");
        collapseBtn.className = "secondary";
        collapseBtn.type = "button";
        collapseBtn.textContent = emb.collapsed ? "Expand" : "Collapse";
        collapseBtn.onclick = () => { emb.collapsed = !emb.collapsed; renderEmbeds(); };
        controls.appendChild(collapseBtn);

        const removeBtn = document.createElement("button");
        removeBtn.className = "secondary";
        removeBtn.type = "button";
        removeBtn.textContent = "Remove";
        removeBtn.onclick = () => removeEmbed(idx);
        if (embeds.length === 1) removeBtn.disabled = true;
        controls.appendChild(removeBtn);

        header.appendChild(title);
        header.appendChild(controls);
        card.appendChild(header);

        const bodyWrap = document.createElement("div");
        bodyWrap.style.display = emb.collapsed ? "none" : "block";

        const formGrid = document.createElement("div");
        formGrid.style.display = "grid";
        formGrid.style.gridTemplateColumns = "1fr 1fr";
        formGrid.style.gap = "12px";
        formGrid.style.marginTop = "12px";

        function addFieldInput(labelText, value, onChange, fullWidth = false, placeholder = "") {
          const wrap = document.createElement("div");
          if (fullWidth) {
            wrap.style.gridColumn = "1 / span 2";
          }
          const lab = document.createElement("label");
          lab.textContent = labelText;
          const input = document.createElement("input");
          input.value = value || "";
          if (placeholder) input.placeholder = placeholder;
          input.oninput = (e) => { onChange(e.target.value); renderPreview(); };
          wrap.appendChild(lab);
          wrap.appendChild(input);
          formGrid.appendChild(wrap);
        }

        // Title & description
        const titleLabel = document.createElement("label");
        titleLabel.textContent = "Title";
        const titleInput = document.createElement("input");
        titleInput.value = emb.title;
        titleInput.placeholder = "Title";
        titleInput.oninput = (e) => { emb.title = e.target.value; renderPreview(); };
        card.appendChild(titleLabel);
        card.appendChild(titleInput);

        const descLabel = document.createElement("label");
        descLabel.textContent = "Description";
        const descInput = document.createElement("textarea");
        descInput.value = emb.description;
        descInput.placeholder = "Description";
        descInput.oninput = (e) => { emb.description = e.target.value; renderPreview(); };
        card.appendChild(descLabel);
        card.appendChild(descInput);

        addFieldInput("Color (hex or name)", emb.color, (v) => { emb.color = v; }, false, "#5865F2 or blurple");
        addFieldInput("Thumbnail URL", emb.thumbnail, (v) => { emb.thumbnail = v; });
        addFieldInput("Image URL", emb.image, (v) => { emb.image = v; });
        addFieldInput("Footer text", emb.footer, (v) => { emb.footer = v; }, true);
        addFieldInput("Author name", emb.author.name, (v) => { emb.author.name = v; });
        addFieldInput("Author icon URL", emb.author.icon_url, (v) => { emb.author.icon_url = v; });

        bodyWrap.appendChild(formGrid);

        const fieldsHeader = document.createElement("div");
        fieldsHeader.style.display = "flex";
        fieldsHeader.style.justifyContent = "space-between";
        fieldsHeader.style.alignItems = "center";
        fieldsHeader.style.marginTop = "12px";
        const fhTitle = document.createElement("h5");
        fhTitle.textContent = "Fields";
        fhTitle.style.margin = "0";
        const addFieldBtn = document.createElement("button");
        addFieldBtn.type = "button";
        addFieldBtn.textContent = "+ Add field";
        addFieldBtn.onclick = () => addField(idx);
        fieldsHeader.appendChild(fhTitle);
        fieldsHeader.appendChild(addFieldBtn);
        bodyWrap.appendChild(fieldsHeader);

        const fieldsContainer = document.createElement("div");
        fieldsContainer.className = "fields";
        renderFields(idx, fieldsContainer);
        bodyWrap.appendChild(fieldsContainer);

        card.appendChild(bodyWrap);

        container.appendChild(card);
      });
      renderPreview();
    }

    function getPayload() {
      const content = document.getElementById("content").value;
      const sanitizedEmbeds = embeds.map(e => ({
        title: e.title,
        description: e.description,
        color: e.color,
        thumbnail: e.thumbnail,
        image: e.image,
        footer: e.footer,
        author: { name: e.author.name, icon_url: e.author.icon_url },
        fields: (e.fields || []).filter(f => f.name || f.value).map(f => ({
          name: f.name,
          value: f.value,
          inline: !!f.inline,
        })),
      }));
      return {
        content,
        embeds: sanitizedEmbeds,
        file_name: fileName,
      };
    }

    function downloadCurrent() {
      const status = document.getElementById("status");
      const payload = getPayload();
      const stamp = new Date().toISOString().replace(/[-:.TZ]/g, "");
      const name = (fileName && fileName.trim()) ? fileName.trim() : `embed_export_${stamp}.json`;
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      status.textContent = `Downloaded ${name}. Use /embed import_file in Discord or copy to your bot host.`;
    }

    function renderPreview() {
      const payload = getPayload();
      const preview = document.getElementById("preview");
      preview.innerHTML = "";

      const shell = document.createElement("div");
      shell.className = "embed-shell";

      if (payload.content) {
        const msg = document.createElement("div");
        msg.className = "message-content";
        msg.textContent = payload.content;
        shell.appendChild(msg);
      }

      payload.embeds.forEach((embedData) => {
        const card = document.createElement("div");
        card.className = "embed-card";

        const colorBar = document.createElement("div");
        colorBar.className = "embed-color";
        colorBar.style.background = embedData.color || "#5865F2";
        card.appendChild(colorBar);

        const body = document.createElement("div");
        body.className = "embed-body";

        if (embedData.author?.name) {
          const authorRow = document.createElement("div");
          authorRow.className = "embed-author";
          if (embedData.author.icon_url) {
            const img = document.createElement("img");
            img.src = embedData.author.icon_url;
            img.className = "thumb";
            img.alt = "Author icon";
            authorRow.appendChild(img);
          }
          const name = document.createElement("span");
          name.textContent = embedData.author.name;
          authorRow.appendChild(name);
          body.appendChild(authorRow);
        }

        if (embedData.title !== undefined && embedData.title !== null && embedData.title !== "") {
          const title = document.createElement("h4");
          title.className = "embed-title";
          title.textContent = embedData.title;
          body.appendChild(title);
        }

        if (embedData.description) {
          const desc = document.createElement("div");
          desc.className = "embed-desc";
          desc.textContent = embedData.description;
          body.appendChild(desc);
        }

        if (embedData.fields && embedData.fields.length) {
          const fieldsWrap = document.createElement("div");
          fieldsWrap.className = "embed-fields";
          embedData.fields.forEach(f => {
            const item = document.createElement("div");
            item.className = "embed-field";
            if (f.inline) item.classList.add("inline");

            const n = document.createElement("div");
            n.className = "embed-field-name";
            n.textContent = f.name;
            const v = document.createElement("div");
            v.className = "embed-field-value";
            v.textContent = f.value;

            item.appendChild(n);
            item.appendChild(v);
            fieldsWrap.appendChild(item);
          });
          body.appendChild(fieldsWrap);
        }

        if (embedData.image) {
          const img = document.createElement("img");
          img.src = embedData.image;
          img.className = "embed-image";
          img.alt = "Embed image";
          body.appendChild(img);
        }

        if (embedData.footer) {
          const footer = document.createElement("div");
          footer.className = "footer";
          footer.textContent = embedData.footer;
          body.appendChild(footer);
        }

        card.appendChild(body);
        shell.appendChild(card);
      });

      preview.appendChild(shell);
    }

    document.getElementById("upload").addEventListener("change", async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const status = document.getElementById("status");
      status.textContent = "Uploading...";
      const form = new FormData();
      form.append("file", file);
      try {
        const res = await fetch(`/upload?file_name=${encodeURIComponent(file.name || fileName)}`, { method: "POST", body: form });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to upload");
        fileName = file.name || fileName;
        document.getElementById("fileName").value = fileName;
        status.textContent = `Uploaded. Saved to ${fileName}. Use /embed import or /embed import_file in Discord.`;
      } catch (err) {
        status.textContent = "Error: " + err.message;
      } finally {
        e.target.value = "";
      }
    });

    document.getElementById("content").addEventListener("input", renderPreview);
    document.getElementById("fileName").addEventListener("input", (e) => {
      fileName = e.target.value || "embed_export.json";
    });
    renderEmbeds();
  </script>
</body>
</html>
"""


@APP.route("/", methods=["GET"])
def index():
    return render_template_string(HTML)


@APP.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    try:
        data = json.load(file)
    except json.JSONDecodeError as exc:
        return jsonify({"error": f"Invalid JSON: {exc}"}), 400

    file_name = request.args.get("file_name") or file.filename or DEFAULT_FILE
    path = safe_json_path(file_name)

    try:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as exc:
        return jsonify({"error": f"Failed to write file: {exc}"}), 500

    return jsonify({"status": "ok", "path": str(path.resolve())})


if __name__ == "__main__":
    APP.run(host="127.0.0.1", port=5000, debug=False)
