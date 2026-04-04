import { useEffect, useState, useCallback } from "react";
import "@/App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

/* ========== ADMIN PANEL ========== */
const AdminPanel = () => {
  const [dashboard, setDashboard] = useState(null);
  const [users, setUsers] = useState([]);
  const [payments, setPayments] = useState([]);
  const [tab, setTab] = useState("overview");
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      const [dashRes, usersRes, paymentsRes] = await Promise.all([
        axios.get(`${API}/admin/dashboard`),
        axios.get(`${API}/admin/users`),
        axios.get(`${API}/admin/payments`),
      ]);
      setDashboard(dashRes.data);
      setUsers(usersRes.data.users || []);
      setPayments(paymentsRes.data.payments || []);
    } catch (e) {
      console.error("Admin fetch error:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const iv = setInterval(fetchAll, 15000);
    return () => clearInterval(iv);
  }, [fetchAll]);

  const handlePremium = async (telegramId, action) => {
    try {
      await axios.post(`${API}/admin/premium`, { telegram_id: telegramId, action });
      await fetchAll();
    } catch (e) {
      console.error(e);
    }
  };

  const handlePayment = async (paymentId, action) => {
    try {
      await axios.post(`${API}/admin/payment-action`, { payment_id: paymentId, action });
      await fetchAll();
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: "#0A0A0A" }}>
        <p style={{ color: "#A1A1AA" }}>Yukleniyor...</p>
      </div>
    );
  }

  const pendingPayments = payments.filter((p) => p.status === "pending");

  return (
    <div className="min-h-screen" style={{ backgroundColor: "#0A0A0A", color: "#fff" }}>
      {/* Tabs */}
      <div className="flex gap-1 p-4 border-b" style={{ borderColor: "rgba(255,255,255,0.1)" }}>
        {["overview", "users", "payments"].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            data-testid={`admin-tab-${t}`}
            className="px-5 py-2 rounded-lg text-sm font-semibold transition-all"
            style={{
              backgroundColor: tab === t ? "#007AFF" : "transparent",
              color: tab === t ? "#fff" : "#A1A1AA",
              border: tab === t ? "none" : "1px solid rgba(255,255,255,0.1)",
              cursor: "pointer",
            }}
          >
            {t === "overview" ? "Genel Bakis" : t === "users" ? `Kullanicilar (${users.length})` : `Odemeler (${pendingPayments.length} bekleyen)`}
          </button>
        ))}
      </div>

      <div className="p-6">
        {tab === "overview" && dashboard && <OverviewTab data={dashboard} />}
        {tab === "users" && <UsersTab users={users} onPremium={handlePremium} />}
        {tab === "payments" && <PaymentsTab payments={payments} onAction={handlePayment} />}
      </div>
    </div>
  );
};

const OverviewTab = ({ data }) => (
  <div>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <MiniStat label="Kullanici" value={data.total_users} color="#007AFF" testId="admin-stat-users" />
      <MiniStat label="Premium" value={data.premium_users} color="#00FF66" testId="admin-stat-premium" />
      <MiniStat label="Toplam Kupon" value={data.total_coupons} color="#FFCC00" testId="admin-stat-coupons" />
      <MiniStat label="Bugun Kupon" value={data.today_coupons} color="#FF3B30" testId="admin-stat-today" />
    </div>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <MiniStat label="Haftalik Kupon" value={data.weekly_coupons} color="#A855F7" testId="admin-stat-weekly" />
      <MiniStat label="Kazanan" value={data.won} color="#00FF66" testId="admin-stat-won" />
      <MiniStat label="Kaybeden" value={data.lost} color="#FF3B30" testId="admin-stat-lost" />
      <MiniStat label="Basari %" value={`${data.win_rate}%`} color="#007AFF" testId="admin-stat-winrate" />
    </div>
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      <MiniStat label="Bekleyen Odeme" value={data.pending_payments} color="#FFCC00" testId="admin-stat-pending" />
      <MiniStat label="Onaylanan Odeme" value={data.approved_payments} color="#00FF66" testId="admin-stat-approved" />
      <MiniStat label="Toplam Gelir" value={`${data.revenue} TL`} color="#A855F7" testId="admin-stat-revenue" />
    </div>
  </div>
);

const UsersTab = ({ users, onPremium }) => (
  <div className="overflow-x-auto">
    <table className="w-full text-left" style={{ borderCollapse: "separate", borderSpacing: "0 8px" }}>
      <thead>
        <tr style={{ color: "#52525B" }}>
          <th className="px-4 py-2 text-xs">Kullanici</th>
          <th className="px-4 py-2 text-xs">Telegram ID</th>
          <th className="px-4 py-2 text-xs">Plan</th>
          <th className="px-4 py-2 text-xs">Kupon</th>
          <th className="px-4 py-2 text-xs">Bitis</th>
          <th className="px-4 py-2 text-xs">Islem</th>
        </tr>
      </thead>
      <tbody>
        {users.map((u, i) => {
          const isPrem = u.is_premium && u.premium_until && new Date(u.premium_until) > new Date();
          return (
            <tr
              key={i}
              className="rounded-lg"
              style={{ backgroundColor: "#141414" }}
              data-testid={`user-row-${i}`}
            >
              <td className="px-4 py-3 rounded-l-lg">
                <span style={{ color: "#fff" }}>@{u.username || "-"}</span>
                {u.is_admin && <span className="ml-2 text-xs px-2 py-0.5 rounded" style={{ backgroundColor: "#FF3B30", color: "#fff" }}>ADMIN</span>}
              </td>
              <td className="px-4 py-3" style={{ color: "#A1A1AA" }}>{u.telegram_id}</td>
              <td className="px-4 py-3">
                <span
                  className="text-xs px-2 py-1 rounded font-semibold"
                  style={{
                    backgroundColor: isPrem ? "rgba(0,255,102,0.15)" : "rgba(255,255,255,0.05)",
                    color: isPrem ? "#00FF66" : "#A1A1AA",
                  }}
                >
                  {isPrem ? "PREMIUM" : "UCRETSIZ"}
                </span>
              </td>
              <td className="px-4 py-3" style={{ color: "#fff" }}>{u.total_coupons || 0}</td>
              <td className="px-4 py-3" style={{ color: "#A1A1AA", fontSize: "12px" }}>
                {isPrem ? u.premium_until?.substring(0, 10) : "-"}
              </td>
              <td className="px-4 py-3 rounded-r-lg">
                {isPrem ? (
                  <button
                    onClick={() => onPremium(u.telegram_id, "deactivate")}
                    className="text-xs px-3 py-1 rounded font-semibold"
                    style={{ backgroundColor: "rgba(255,59,48,0.15)", color: "#FF3B30", border: "none", cursor: "pointer" }}
                    data-testid={`deactivate-premium-${i}`}
                  >
                    Kaldir
                  </button>
                ) : (
                  <button
                    onClick={() => onPremium(u.telegram_id, "activate")}
                    className="text-xs px-3 py-1 rounded font-semibold"
                    style={{ backgroundColor: "rgba(0,255,102,0.15)", color: "#00FF66", border: "none", cursor: "pointer" }}
                    data-testid={`activate-premium-${i}`}
                  >
                    Premium Ver
                  </button>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  </div>
);

const PaymentsTab = ({ payments, onAction }) => (
  <div className="space-y-4">
    {payments.length === 0 ? (
      <p style={{ color: "#52525B", textAlign: "center", padding: "40px" }}>Odeme kaydi yok.</p>
    ) : (
      payments.map((p, i) => (
        <div
          key={i}
          className="p-4 rounded-lg border flex items-center justify-between"
          style={{ backgroundColor: "#141414", borderColor: "rgba(255,255,255,0.1)" }}
          data-testid={`payment-row-${i}`}
        >
          <div>
            <div className="flex items-center gap-3 mb-1">
              <span style={{ color: "#fff", fontWeight: "600" }}>@{p.username || "-"}</span>
              <span className="text-xs" style={{ color: "#A1A1AA" }}>#{p.id}</span>
              <span
                className="text-xs px-2 py-0.5 rounded font-semibold"
                style={{
                  backgroundColor:
                    p.status === "pending" ? "rgba(255,204,0,0.15)" : p.status === "approved" ? "rgba(0,255,102,0.15)" : "rgba(255,59,48,0.15)",
                  color: p.status === "pending" ? "#FFCC00" : p.status === "approved" ? "#00FF66" : "#FF3B30",
                }}
              >
                {p.status === "pending" ? "BEKLIYOR" : p.status === "approved" ? "ONAYLANDI" : "REDDEDILDI"}
              </span>
            </div>
            <div className="text-xs" style={{ color: "#52525B" }}>
              {p.amount} TL | {p.created_at?.substring(0, 16).replace("T", " ")}
            </div>
          </div>
          {p.status === "pending" && (
            <div className="flex gap-2">
              <button
                onClick={() => onAction(p.id, "approve")}
                className="text-xs px-4 py-2 rounded font-semibold"
                style={{ backgroundColor: "#00FF66", color: "#000", border: "none", cursor: "pointer" }}
                data-testid={`approve-payment-${i}`}
              >
                Onayla
              </button>
              <button
                onClick={() => onAction(p.id, "reject")}
                className="text-xs px-4 py-2 rounded font-semibold"
                style={{ backgroundColor: "#FF3B30", color: "#fff", border: "none", cursor: "pointer" }}
                data-testid={`reject-payment-${i}`}
              >
                Reddet
              </button>
            </div>
          )}
        </div>
      ))
    )}
  </div>
);

const MiniStat = ({ label, value, color, testId }) => (
  <div
    className="p-4 rounded-xl border"
    style={{ backgroundColor: "#141414", borderColor: "rgba(255,255,255,0.1)" }}
    data-testid={testId}
  >
    <div className="text-xs mb-1" style={{ color: "#52525B" }}>{label}</div>
    <div className="text-2xl font-bold" style={{ color, fontFamily: "Bebas Neue", letterSpacing: "-0.03em" }}>{value}</div>
  </div>
);

/* ========== MAIN APP ========== */
function App() {
  const [page, setPage] = useState("admin");

  return (
    <div className="App">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-3 border-b" style={{ backgroundColor: "#0A0A0A", borderColor: "rgba(255,255,255,0.1)" }}>
        <h1 className="text-xl font-bold" style={{ color: "#fff", fontFamily: "Bebas Neue", letterSpacing: "-0.03em" }} data-testid="nav-title">
          BETTING BOT
        </h1>
        <div className="flex gap-2">
          <button
            onClick={() => setPage("admin")}
            data-testid="nav-admin"
            className="px-4 py-1.5 rounded-lg text-sm font-semibold"
            style={{
              backgroundColor: page === "admin" ? "#007AFF" : "transparent",
              color: page === "admin" ? "#fff" : "#A1A1AA",
              border: page === "admin" ? "none" : "1px solid rgba(255,255,255,0.1)",
              cursor: "pointer",
            }}
          >
            Admin Panel
          </button>
        </div>
      </nav>
      {page === "admin" && <AdminPanel />}
    </div>
  );
}

export default App;
