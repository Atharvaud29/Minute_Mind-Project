document.addEventListener("DOMContentLoaded", function(){

  /* Sidebar click behavior (smooth scroll to panel) */
  const navItems = document.querySelectorAll(".left-nav .nav-item");
  navItems.forEach(item=>{
    item.addEventListener("click", function(e){
      e.preventDefault();
      navItems.forEach(n=>n.classList.remove("active"));
      item.classList.add("active");
      const target = item.dataset.target;
      if(!target) return;
      const el = document.getElementById(target);
      if(el){
        el.scrollIntoView({behavior:"smooth", block:"center"});
        el.style.transition = "box-shadow .25s ease";
        el.style.boxShadow = "0 14px 36px rgba(6,22,23,0.08)";
        setTimeout(()=> el.style.boxShadow = "", 700);
      }
    });
  });

  /* Tab switching (right column) */
  function switchToTab(name){
    document.querySelectorAll(".tab-btn").forEach(b=>b.classList.remove("active"));
    let btn = document.querySelector('.tab-btn[data-tab="'+name+'"]');
    if(btn) btn.classList.add("active");
    document.querySelectorAll(".tab-content").forEach(tc=> tc.classList.add("hidden"));
    let el = document.getElementById(name);
    if(el) el.classList.remove("hidden");
  }
  document.querySelectorAll(".tab-btn").forEach(btn=>{
    btn.onclick = function(){ switchToTab(btn.dataset.tab); }
  });

  /* Demo / table utilities (preserve functionality) */
  function clearTable(tableId){ const tbody = document.getElementById(tableId).querySelector("tbody"); if(tbody) tbody.innerHTML = ""; }
  
  function addTaskRow(data){
    const tbody = document.getElementById("tasksTable").querySelector("tbody");
    if(!tbody) return;
    const tr = document.createElement("tr");
    
    // Apply status color class
    const statusClass = getStatusClass(data.status);
    
    tr.innerHTML = `
      <td contenteditable="true">${data.task || ""}</td>
      <td contenteditable="true">${data.assignee || ""}</td>
      <td contenteditable="true">${data.due || ""}</td>
      <td contenteditable="true" class="${statusClass}">${data.status || "Pending"}</td>
      <td contenteditable="true">${data.notes || ""}</td>
      <td><button class="row-btn" onclick="this.closest('tr').remove()">🗑️ Delete</button></td>
    `;
    tbody.appendChild(tr);
    
    // Add subtle animation
    tr.style.opacity = "0";
    tr.style.transform = "translateY(10px)";
    setTimeout(() => {
      tr.style.transition = "all 0.3s ease";
      tr.style.opacity = "1";
      tr.style.transform = "translateY(0)";
    }, 10);
  }
  
  function addConflictRow(data){
    const tbody = document.getElementById("conflictsTable").querySelector("tbody");
    if(!tbody) return;
    const tr = document.createElement("tr");
    
    // Apply severity color class
    const severityClass = getSeverityClass(data.severity);
    
    tr.innerHTML = `
      <td contenteditable="true">${data.conflict || ""}</td>
      <td contenteditable="true">${data.owner || ""}</td>
      <td contenteditable="true" class="${severityClass}">${data.severity || "Low"}</td>
      <td contenteditable="true">${data.notes || ""}</td>
      <td><button class="row-btn" onclick="this.closest('tr').remove()">🗑️ Delete</button></td>
    `;
    tbody.appendChild(tr);
    
    // Add subtle animation
    tr.style.opacity = "0";
    tr.style.transform = "translateY(10px)";
    setTimeout(() => {
      tr.style.transition = "all 0.3s ease";
      tr.style.opacity = "1";
      tr.style.transform = "translateY(0)";
    }, 10);
  }
  
  // Helper functions for color classes
  function getStatusClass(status) {
    switch(status) {
      case 'Pending': return 'status-pending';
      case 'In Progress': return 'status-in-progress';
      case 'Done': return 'status-done';
      default: return 'status-pending';
    }
  }
  
  function getSeverityClass(severity) {
    switch(severity) {
      case 'Low': return 'severity-low';
      case 'Medium': return 'severity-medium';
      case 'High': return 'severity-high';
      default: return 'severity-low';
    }
  }
  
  window.addTaskRow = addTaskRow;
  window.addConflictRow = addConflictRow;

  // Add buttons
  const addTaskBtn = document.getElementById("addTaskBtn");
  if(addTaskBtn){
    addTaskBtn.addEventListener("click", function(e){
      e.preventDefault();
      const t = document.getElementById("task_title").value.trim();
      const a = document.getElementById("task_assignee").value.trim();
      const d = document.getElementById("task_due").value.trim();
      const s = document.getElementById("task_status").value;
      if(!t || !a){ alert("Please add Task title and Assignee"); return; }
      addTaskRow({task:t, assignee:a, due:d, status:s});
      document.getElementById("task_title").value = ""; document.getElementById("task_assignee").value = ""; document.getElementById("task_due").value = "";
    });
  }
  const addConflictBtn = document.getElementById("addConflictBtn");
  if(addConflictBtn){
    addConflictBtn.addEventListener("click", function(e){
      e.preventDefault();
      const c = document.getElementById("conf_summary").value.trim();
      const o = document.getElementById("conf_owner").value.trim();
      const sev = document.getElementById("conf_severity").value;
      if(!c){ alert("Please provide conflict summary"); return; }
      addConflictRow({conflict:c, owner:o, severity:sev});
      document.getElementById("conf_summary").value = ""; document.getElementById("conf_owner").value = "";
    });
  }

  // Export helper
  function exportTableToCSV(tableId, filename){
    const rows = Array.from(document.getElementById(tableId).querySelectorAll("tr"));
    const csv = rows.map(r=>{
      const cells = Array.from(r.querySelectorAll("th, td")).map(c=>{
        return '"' + c.innerText.replace(/"/g,'""').replace(/\n/g,' ').trim() + '"';
      });
      return cells.join(",");
    }).join("\n");
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url); link.setAttribute("download", filename); link.style.visibility = 'hidden';
    document.body.appendChild(link); link.click(); document.body.removeChild(link);
  }
  const exportTasks = document.getElementById("exportTasks");
  if(exportTasks) exportTasks.addEventListener("click", ()=> exportTableToCSV("tasksTable","tasks.csv"));
  const exportConflicts = document.getElementById("exportConflicts");
  if(exportConflicts) exportConflicts.addEventListener("click", ()=> exportTableToCSV("conflictsTable","conflicts.csv"));

  // Save summary (demo)
  const summSave = document.getElementById("summ-save");
  if(summSave) summSave.addEventListener("click", ()=> alert("Summary saved (demo)."));

  const summClear = document.getElementById("summ-clear");
  if(summClear) summClear.addEventListener("click", ()=> document.getElementById("summaryText").value = "");

  const copyFinal = document.getElementById("copyFinal");
  if(copyFinal){
    copyFinal.addEventListener("click", function(){ const val = document.getElementById("finalMomEditor").value; navigator.clipboard.writeText(val).then(()=>alert("Final MoM copied to clipboard")); });
  }

});
