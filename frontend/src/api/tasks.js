// import { http } from './http'

// export const fetchTasks = async () => {
//   const { data } = await http.get('/tasks')
//   return data
// }

// export const updateTask = async (id, payload) => {
//   const { data } = await http.patch(`/tasks/${id}`, payload)
//   return data
// }

// export const createTask = async (payload) => {
//   const { data } = await http.post('/tasks', payload)
//   return data
// }

// import { http } from './http'

// // Fetch all tasks
// export const fetchTasks = async () => {
//   const { data } = await http.get('/tasks')
//   return data
// }

// // Update a specific task by ID
// export const updateTask = async (id, payload) => {
//   const { data } = await http.patch(`/tasks/${id}`, payload)
//   return data
// }

// // Create a new task
// export const createTask = async (payload) => {
//   const { data } = await http.post('/tasks', payload)
//   return data
// }
import { http } from "./http";

/* ============================================================
   FETCH ALL TASKS
   ============================================================ */
export const fetchTasks = async () => {
  const { data } = await http.get("/tasks");
  return data;
};

/* ============================================================
   CREATE A TASK
   Backend expects:
   {
     person: "",
     task: "",
     deadline: "",
     status?: "",
     notes?: "",
     meeting_id?: number
   }
   ============================================================ */
export const createTask = async (payload) => {
  const { data } = await http.post("/tasks", payload);
  return data;
};

/* ============================================================
   UPDATE A TASK BY ID
   Any of these can be updated:
   person, task, deadline, status, notes
   ============================================================ */
export const updateTask = async (id, payload) => {
  const { data } = await http.patch(`/tasks/${id}`, payload);
  return data;
};
