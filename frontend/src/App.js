import { useEffect, useState } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { 
  ActivityIcon as Activity, 
  TrendUp, 
  UsersIcon as Users, 
  FileTextIcon as FileText, 
  TargetIcon as Target, 
  ChartBarIcon as BarChart3,
  ArrowClockwise,
  BrainIcon as Brain,
  TrophyIcon as Trophy,
  ClockIcon as Clock
} from "@phosphor-icons/react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [matches, setMatches] = useState([]);
  const [coupons, setCoupons] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, matchesRes, couponsRes, predictionsRes] = await Promise.all([
        axios.get(`${API}/stats`),
        axios.get(`${API}/matches/today`),
        axios.get(`${API}/coupons/recent`),
        axios.get(`${API}/predictions/recent`)
      ]);
      
      setStats(statsRes.data);
      setMatches(matchesRes.data.matches || []);
      setCoupons(couponsRes.data.coupons || []);
      setPredictions(predictionsRes.data.predictions || []);
      setLoading(false);
    } catch (e) {
      console.error("Error fetching data:", e);
      setLoading(false);
    }
  };

  const triggerScrape = async () => {
    try {
      await axios.post(`${API}/scrape/trigger`);
      await fetchData();
      alert("Maçlar başarıyla yüklendi!");
    } catch (e) {
      console.error("Error triggering scrape:", e);
      alert("Hata oluştu!");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: '#0A0A0A' }}>
        <div className="text-center">
          <ArrowClockwise size={48} className="animate-spin mx-auto mb-4" style={{ color: '#007AFF' }} />
          <p className="text-lg" style={{ color: '#A1A1AA' }}>Yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#0A0A0A', padding: '24px' }}>
      {/* Header */}
      <div 
        className="mb-8 p-8 rounded-xl border"
        style={{
          backgroundColor: '#141414',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: '1px'
        }}
      >
        <div className="flex items-center justify-between">
          <div>
            <h1 
              className="text-5xl mb-2"
              style={{ 
                fontFamily: 'Bebas Neue',
                letterSpacing: '-0.05em',
                color: '#FFFFFF'
              }}
              data-testid="dashboard-title"
            >
              🎯 BETTING BOT DASHBOARD
            </h1>
            <p className="text-base" style={{ color: '#A1A1AA' }}>Yapay zeka destekli futbol analiz sistemi</p>
          </div>
          <button
            onClick={triggerScrape}
            className="px-6 py-3 rounded-lg font-semibold flex items-center gap-2"
            style={{
              backgroundColor: '#007AFF',
              color: '#FFFFFF',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={(e) => e.target.style.backgroundColor = '#0062CC'}
            onMouseLeave={(e) => e.target.style.backgroundColor = '#007AFF'}
            data-testid="trigger-scrape-button"
          >
            <ArrowClockwise size={20} />
            Maçları Yükle
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={<Users size={32} weight="bold" />}
          title="Toplam Kullanıcı"
          value={stats?.total_users || 0}
          color="#007AFF"
          testId="total-users-stat"
        />
        <StatCard
          icon={<FileText size={32} weight="bold" />}
          title="Oluşturulan Kupon"
          value={stats?.total_coupons || 0}
          color="#00FF66"
          testId="total-coupons-stat"
        />
        <StatCard
          icon={<Target size={32} weight="bold" />}
          title="Analiz Edilen Maç"
          value={stats?.total_matches || 0}
          color="#FF3B30"
          testId="total-matches-stat"
        />
        <StatCard
          icon={<Brain size={32} weight="bold" />}
          title="AI Tahmini"
          value={stats?.total_predictions || 0}
          color="#FFCC00"
          testId="total-predictions-stat"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Today's Matches */}
        <div className="lg:col-span-2">
          <ContentCard title="Bugünkü Maçlar" icon={<Activity size={24} weight="bold" />}>
            {matches.length === 0 ? (
              <div className="text-center py-8" style={{ color: '#52525B' }}>
                <Trophy size={48} className="mx-auto mb-4" />
                <p>Bugün için maç bulunamadı.</p>
                <button
                  onClick={triggerScrape}
                  className="mt-4 px-4 py-2 rounded-lg"
                  style={{
                    backgroundColor: '#141414',
                    border: '1px solid rgba(255,255,255,0.1)',
                    color: '#007AFF',
                    cursor: 'pointer'
                  }}
                  data-testid="load-matches-button"
                >
                  Maçları Yükle
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {matches.slice(0, 10).map((match, idx) => (
                  <div
                    key={idx}
                    className="match-row p-4 rounded-lg border"
                    style={{
                      backgroundColor: '#0A0A0A',
                      borderColor: 'rgba(255,255,255,0.1)',
                      borderWidth: '1px'
                    }}
                    data-testid={`match-item-${idx}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="text-xs mb-1" style={{ color: '#52525B' }}>
                          {match.league}
                        </div>
                        <div className="font-semibold" style={{ color: '#FFFFFF' }}>
                          {match.home_team} vs {match.away_team}
                        </div>
                      </div>
                      <div className="flex gap-3 items-center">
                        <div className="text-center">
                          <div className="text-xs" style={{ color: '#52525B' }}>1</div>
                          <div className="font-bold" style={{ color: '#00FF66' }}>{match.odds_1}</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs" style={{ color: '#52525B' }}>X</div>
                          <div className="font-bold" style={{ color: '#007AFF' }}>{match.odds_x}</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs" style={{ color: '#52525B' }}>2</div>
                          <div className="font-bold" style={{ color: '#FF3B30' }}>{match.odds_2}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ContentCard>
        </div>

        {/* Recent Coupons */}
        <div>
          <ContentCard title="Son Kuponlar" icon={<FileText size={24} weight="bold" />}>
            {coupons.length === 0 ? (
              <div className="text-center py-8" style={{ color: '#52525B' }}>
                <FileText size={48} className="mx-auto mb-4" />
                <p>Henüz kupon oluşturulmamış.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {coupons.slice(0, 8).map((coupon, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-lg border"
                    style={{
                      backgroundColor: '#0A0A0A',
                      borderColor: 'rgba(255,255,255,0.1)',
                      borderWidth: '1px'
                    }}
                    data-testid={`coupon-item-${idx}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className={`risk-badge risk-${coupon.risk_level}`}>
                        {coupon.risk_level.toUpperCase()}
                      </span>
                      <span className="font-bold text-lg" style={{ color: '#00FF66' }}>
                        {coupon.total_odds}x
                      </span>
                    </div>
                    <div className="text-sm" style={{ color: '#A1A1AA' }}>
                      {coupon.match_count} maç
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ContentCard>
        </div>
      </div>

      {/* AI Predictions */}
      <div className="mt-6">
        <ContentCard title="AI Analiz Logları" icon={<Brain size={24} weight="bold" />}>
          {predictions.length === 0 ? (
            <div className="text-center py-8" style={{ color: '#52525B' }}>
              <Brain size={48} className="mx-auto mb-4" />
              <p>Henüz AI tahmini yok.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {predictions.slice(0, 6).map((pred, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-lg border"
                  style={{
                    backgroundColor: '#0A0A0A',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: '1px'
                  }}
                  data-testid={`prediction-item-${idx}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs px-2 py-1 rounded" style={{ backgroundColor: '#141414', color: '#007AFF' }}>
                      {pred.ai_model}
                    </span>
                    <span className="font-bold" style={{ color: '#00FF66' }}>
                      {pred.confidence}%
                    </span>
                  </div>
                  <div className="text-sm mb-1" style={{ color: '#FFFFFF' }}>
                    Tahmin: <span className="font-bold">{pred.recommended_bet}</span> @ {pred.predicted_odds}
                  </div>
                  <div className="text-xs" style={{ color: '#52525B' }}>
                    {pred.ai_analysis?.substring(0, 100)}...
                  </div>
                </div>
              ))}
            </div>
          )}
        </ContentCard>
      </div>

      {/* Recent Activities */}
      <div className="mt-6">
        <ContentCard title="Son Aktiviteler" icon={<Clock size={24} weight="bold" />}>
          {stats?.recent_activities?.length === 0 ? (
            <div className="text-center py-8" style={{ color: '#52525B' }}>
              <Activity size={48} className="mx-auto mb-4" />
              <p>Henüz aktivite yok.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {stats?.recent_activities?.slice(0, 5).map((activity, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg border flex items-center justify-between"
                  style={{
                    backgroundColor: '#0A0A0A',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: '1px'
                  }}
                  data-testid={`activity-item-${idx}`}
                >
                  <div>
                    <span className="font-semibold" style={{ color: '#FFFFFF' }}>
                      {activity.activity_type}
                    </span>
                    <span className="text-sm ml-2" style={{ color: '#52525B' }}>
                      User: {activity.user_telegram_id}
                    </span>
                  </div>
                  <div className="text-xs" style={{ color: '#52525B' }}>
                    {new Date(activity.timestamp).toLocaleString('tr-TR')}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ContentCard>
      </div>
    </div>
  );
};

const StatCard = ({ icon, title, value, color, testId }) => {
  return (
    <div
      className="stat-card p-6 rounded-xl border"
      style={{
        backgroundColor: '#141414',
        borderColor: 'rgba(255,255,255,0.1)',
        borderWidth: '1px'
      }}
      data-testid={testId}
    >
      <div className="flex items-start justify-between mb-4">
        <div style={{ color }}>{icon}</div>
      </div>
      <div>
        <div
          className="text-5xl font-bold mb-1"
          style={{ fontFamily: 'Bebas Neue', color: '#FFFFFF', letterSpacing: '-0.05em' }}
        >
          {value}
        </div>
        <div className="text-sm" style={{ color: '#A1A1AA' }}>
          {title}
        </div>
      </div>
    </div>
  );
};

const ContentCard = ({ title, icon, children }) => {
  return (
    <div
      className="p-6 rounded-xl border"
      style={{
        backgroundColor: '#141414',
        borderColor: 'rgba(255,255,255,0.1)',
        borderWidth: '1px'
      }}
    >
      <div className="flex items-center gap-3 mb-4">
        <div style={{ color: '#007AFF' }}>{icon}</div>
        <h2
          className="text-2xl"
          style={{ fontFamily: 'Bebas Neue', color: '#FFFFFF', letterSpacing: '-0.05em' }}
        >
          {title}
        </h2>
      </div>
      {children}
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;