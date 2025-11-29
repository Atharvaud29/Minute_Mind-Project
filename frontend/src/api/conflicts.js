// import { http } from './http'

// export const fetchConflicts = async () => {
//   const { data } = await http.get('/conflicts')
//   return data
// }

// export const updateConflict = async (id, payload) => {
//   const { data } = await http.patch(`/conflicts/${id}`, payload)
//   return data
// }

// export const createConflict = async (payload) => {
//   const { data } = await http.post('/conflicts', payload)
//   return data
// }

// import { http } from './http'

// // Fetch all conflicts
// export const fetchConflicts = async () => {
//   const { data } = await http.get('/conflicts')
//   return data
// }

// // Create a new conflict
// export const createConflict = async (payload) => {
//   const { data } = await http.post('/conflicts', payload)
//   return data
// }

// // Update a specific conflict by ID
// export const updateConflict = async (id, payload) => {
//   const { data } = await http.patch(`/conflicts/${id}`, payload)
//   return data
// }
import { http } from "./http";

/* ============================================================
   FETCH ALL CONFLICTS
   ============================================================ */
export const fetchConflicts = async () => {
  const { data } = await http.get("/conflicts");
  return data;
};

/* ============================================================
   CREATE A NEW CONFLICT
   Backend expects:
   {
     issue: "",
     raised_by: "",
     resolution: "",
     severity: "Low" | "Medium" | "High",
     participants?: "",
     stance?: "",
     topic?: "",
     meeting_id?: number
   }
   ============================================================ */
export const createConflict = async (payload) => {
  const { data } = await http.post("/conflicts", payload);
  return data;
};

/* ============================================================
   UPDATE CONFLICT BY ID
   Can update fields:
   issue, raised_by, resolution, severity
   ============================================================ */
export const updateConflict = async (id, payload) => {
  const { data } = await http.patch(`/conflicts/${id}`, payload);
  return data;
};
