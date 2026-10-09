import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import AuthPage from "@/pages/AuthPage";
import Marketplace from "@/pages/Marketplace";
import ProductDetail from "@/pages/ProductDetail";
import Wallet from "@/pages/Wallet";
import Vault from "@/pages/Vault";
import Orders from "@/pages/Orders";
import Notifications from "@/pages/Notifications";
import Account from "@/pages/Account";
import VendorDashboard from "@/pages/VendorDashboard";
import AdminPanel from "@/pages/AdminPanel";
import Vendors from "@/pages/Vendors";

function Protected({ children, roles }) {
  const { user } = useAuth();
  if (user === null) return <div className="p-10 text-center font-mono text-sm text-slate-500">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster theme="dark" position="top-right" richColors />
        <Routes>
          <Route path="/login" element={<AuthPage mode="login" />} />
          <Route path="/register" element={<AuthPage mode="register" />} />
          <Route element={<Layout />}>
            <Route path="/" element={<Marketplace />} />
            <Route path="/product/:id" element={<ProductDetail />} />
            <Route path="/vendors" element={<Vendors />} />
            <Route path="/wallet" element={<Protected><Wallet /></Protected>} />
            <Route path="/vault" element={<Protected><Vault /></Protected>} />
            <Route path="/orders" element={<Protected><Orders /></Protected>} />
            <Route path="/notifications" element={<Protected><Notifications /></Protected>} />
            <Route path="/account" element={<Protected><Account /></Protected>} />
            <Route path="/vendor" element={<Protected roles={["vendor"]}><VendorDashboard /></Protected>} />
            <Route path="/admin" element={<Protected roles={["admin"]}><AdminPanel /></Protected>} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
