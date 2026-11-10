document.querySelectorAll("[data-example]").forEach(
  (button) =>
    (button.onclick = async () => {
      if ($("submit").disabled) return;
      $("error").textContent = "";
      $("submit").disabled = true;
      $("progress").textContent = "正在读取明确标注的模拟材料…";
      try {
        const response = await fetch("/api/demo/" + button.dataset.example);
        if (!response.ok) throw Error("模拟材料暂不可用");
        const blob = await response.blob();
        const data = new FormData();
        data.append("file", blob, button.dataset.example + ".mp3");
        data.append("context", "公开演示：合成语音模拟，不是真实求助。");
        $("file").value = "";
        $("filename").textContent = button.textContent + "（模拟合成语音）";
        $("preview").replaceChildren();
        if (previewURL) URL.revokeObjectURL(previewURL);
        previewURL = URL.createObjectURL(blob);
        const audio = document.createElement("audio");
        audio.src = previewURL;
        audio.controls = true;
        $("preview").append(audio);
        const { job_id } = await api("/api/analyze", {
          method: "POST",
          body: data,
        });
        for (;;) {
          const job = await api("/api/jobs/" + job_id);
          $("progress").textContent = job.message;
          if (job.status === "completed") {
            render(job.result);
            break;
          }
          if (job.status === "failed") throw Error(job.message);
          await new Promise((resolve) => setTimeout(resolve, 1500));
        }
      } catch (error) {
        $("error").textContent = error.message;
      } finally {
        $("submit").disabled = false;
      }
    }),
);
const originalRender = render;
render = function (data) {
  originalRender(data);
  if (!data.transcript) return;
  const details = document.createElement("details");
  details.className = "card transcript-editor";
  const summary = document.createElement("summary");
  summary.textContent = "听错了？修改转写文字";
  details.append(summary);
  const form = document.createElement("form");
  const label = document.createElement("label");
  label.className = "field";
  label.textContent = "对照原音修改；不会改变声音和画面检测分数";
  const input = document.createElement("textarea");
  input.maxLength = 4000;
  input.required = true;
  input.value = data.transcript.text || "";
  label.append(input);
  form.append(label);
  const save = document.createElement("button");
  save.className = "primary";
  save.textContent = "保存校正并重新检查文字";
  form.append(save);
  const message = document.createElement("p");
  message.setAttribute("role", "status");
  form.append(message);
  form.onsubmit = async (event) => {
    event.preventDefault();
    save.disabled = true;
    try {
      const body = new FormData();
      body.append("text", input.value);
      render(
        await api("/api/cases/" + data.id + "/transcript", {
          method: "POST",
          body,
        }),
      );
    } catch (error) {
      message.textContent = error.message;
      save.disabled = false;
    }
  };
  details.append(form);
  $("result").append(details);
};
