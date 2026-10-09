import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

export function useFetch(url, params) {
  const [data, setData] = useState(null);
  const key = JSON.stringify(params || {});
  const reload = useCallback(() => api.get(url, { params }).then((r) => setData(r.data)), [url, key]); // eslint-disable-line
  useEffect(() => { reload(); }, [reload]);
  return [data, reload];
}
