import { useState, useEffect } from "react";
import {
  Search,
  MapPin,
  ChevronDown,
  AlignJustify,
  X,
  LogOut,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Header() {
  const [activeNav, setActiveNav] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  let navLinks = [
    { label: "BH BANK", isBrand: true, children: null },
    { label: "Agent d'accueil", children: null },
    { label: "Agent de réclamation", children: null },
    { label: "Agent commercial", children: null },
    { label: "Agent de détection de fraude", children: null },
    { label: "Agent d'analyse et de reporting", children: null },
    { label: "Agent de signature et chèques", children: null },
  ];

  if (user) {
    if (user.role === "customer") {
      navLinks = [
        { label: "BH BANK", isBrand: true, to: "/dashboard" },
        { label: "Agent d'accueil", to: "/bank-agent" },
        { label: "Agent d'analyse ", to: "/dashboard" },
        { label: "Agent de crédit", to: "/credit-agent" },
        { label: "Agent de réclamation", to: "/complaint-agent" },
        { label: "Agent de détection de fraude", to: "/dashboard" },
        { label: "Agent commercial", to: "/dashboard" },
      ];
    } else {
      navLinks = [
        { label: 'BH BANK', isBrand: true, to: '/dashboard' },
        { label: 'Agent de détection de fraude', to: '/dashboard' },
        { label: 'Agent d\'analyse et de reporting', to: '/reporting' },
        { label: 'Agent de signature et chèques', to: '/dashboard' },
      ];
    }
  }

  // Map roles to French for display
  const roleDisplayMap: { [key: string]: string } = {
    customer: "Client",
    "chef of agency": "Chef d'agence",
  };
  const displayRole = user
    ? roleDisplayMap[user.role.toLowerCase()] || user.role
    : "";

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-50 w-full transition-shadow duration-300 ${scrolled ? "shadow-lg" : ""}`}
    >
      {/* ── Top white bar ── */}
      <div
        className={`bg-white transition-all duration-300 ${scrolled ? "opacity-95 backdrop-blur-sm" : ""}`}
      >
        <div className="max-w-screen-xl mx-auto px-4 lg:px-6 flex items-center justify-between h-[68px]">
          {/* Logo */}
          <a
            href={user ? "/dashboard" : "/"}
            className="flex items-center shrink-0"
          >
            <img src="/logobh.svg" alt="BH Bank" className="h-[42px] w-auto" />
          </a>

          {/* Right actions */}
          <div className="flex items-center gap-2 md:gap-3">
            {/* ROLE Display */}
            <div className="bg-[#1c2951] text-white px-4 py-2 rounded-full text-sm font-semibold whitespace-nowrap uppercase cursor-default">
              {user ? displayRole : "NON CONNECTÉ"}
            </div>

            {/* Authenticated User or Login button */}
            {user ? (
              <div className="hidden lg:flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <img
                    src={
                      user.picture ||
                      "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png"
                    }
                    alt="Avatar"
                    className="w-8 h-8 rounded-full border border-gray-200 object-cover"
                  />
                  <span
                    className="text-sm font-medium text-gray-700 max-w-[100px] truncate"
                    title={user.name}
                  >
                    {user.name}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-1.5 text-gray-500 hover:text-[#c8102e] hover:bg-red-50 rounded-full transition"
                  title="Se déconnecter"
                >
                  <LogOut size={18} />
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                className="bg-[#c8102e] text-white px-4 py-2 rounded-full text-sm font-semibold hover:bg-red-700 transition-colors whitespace-nowrap hidden lg:block"
              >
                SE CONNECTER
              </Link>
            )}

            {/* Hamburger circle button */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="w-9 h-9 rounded-full border-2 border-gray-200 flex items-center justify-center text-gray-600 hover:border-[#c8102e] hover:text-[#c8102e] transition-all"
            >
              {mobileOpen ? <X size={15} /> : <AlignJustify size={15} />}
            </button>
          </div>
        </div>

        {/* Search bar dropdown */}
        {searchOpen && (
          <div className="border-t border-gray-100 bg-white px-6 py-3">
            <div className="max-w-screen-xl mx-auto">
              <div className="relative">
                <Search
                  size={16}
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400"
                />
                <input
                  autoFocus
                  type="text"
                  placeholder="Rechercher sur le site..."
                  className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-full text-sm focus:outline-none focus:border-[#c8102e] focus:ring-2 focus:ring-[#c8102e]/20"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Dark navy nav bar ── */}
      <div
        className={`bg-[#1c2951] transition-all duration-300 hidden ${mobileOpen ? "lg:block" : "lg:hidden"}`}
      >
        <div className="max-w-screen-xl mx-auto px-4 lg:px-6 flex items-center justify-between h-10">
          <nav className="flex items-center h-full">
            {navLinks.map((item: any, idx) => (
              <div
                key={item.label}
                className="relative h-full flex items-center group"
                onMouseEnter={() => item.children && setActiveNav(item.label)}
                onMouseLeave={() => setActiveNav(null)}
              >
                <Link
                  to={item.to || "#"}
                  className={`flex items-center gap-1 h-full px-3.5 text-[13px] font-medium transition-colors whitespace-nowrap
                    ${idx === 0
                      ? "text-white font-bold border-r border-[#ffffff30]"
                      : "text-gray-300 hover:text-white"
                    }
                  `}
                >
                  {item.label}
                  {item.children && (
                    <ChevronDown
                      size={11}
                      className={`transition-transform duration-200 ${activeNav === item.label ? "rotate-180" : ""}`}
                    />
                  )}
                  {/* Underline hover effect */}
                  <span className="absolute bottom-0 left-0 w-full h-[3px] bg-[#c8102e] scale-x-0 group-hover:scale-x-100 transition-transform origin-left duration-300" />
                </Link>

                {/* Dropdown */}
                {item.children && activeNav === item.label && (
                  <div className="absolute top-full left-0 bg-white shadow-xl min-w-52 py-2 z-50 border-t-2 border-[#c8102e]">
                    {item.children.map((child) => (
                      <a
                        key={child}
                        href="#"
                        className="block px-5 py-2.5 text-gray-700 text-sm hover:bg-red-50 hover:text-[#c8102e] transition-colors"
                      >
                        {child}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </nav>

          {/* Language selector */}
          <button className="flex items-center gap-1 text-gray-300 hover:text-white text-[13px] font-medium transition-colors">
            Français <ChevronDown size={11} />
          </button>
        </div>
      </div>

      {/* ── Mobile menu ── */}
      {mobileOpen && (
        <div className="lg:hidden bg-white border-t border-gray-100 shadow-xl">
          <div className="px-4 py-2">
            {/* Mobile Auth */}
            {user ? (
              <div className="mb-4 mt-2">
                <div className="flex items-center gap-3 px-2 py-3 bg-gray-50 rounded-xl mb-2 border border-gray-100">
                  <img
                    src={
                      user.picture ||
                      "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png"
                    }
                    alt="Avatar"
                    className="w-10 h-10 rounded-full border border-gray-200 object-cover"
                  />
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold text-gray-900">
                      {user.name}
                    </span>
                    <span className="text-xs text-gray-500">
                      {user.email || "Connecté"}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => {
                    handleLogout();
                    setMobileOpen(false);
                  }}
                  className="w-full flex items-center justify-center gap-2 bg-gray-100 text-gray-700 py-2.5 rounded-full text-sm font-semibold hover:bg-red-50 hover:text-[#c8102e] transition-colors"
                >
                  <LogOut size={16} /> DÉCONNEXION
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                onClick={() => setMobileOpen(false)}
                className="block w-full text-center bg-[#c8102e] text-white py-2.5 rounded-full text-sm font-semibold mb-3 mt-2"
              >
                SE CONNECTER
              </Link>
            )}
            {navLinks.slice(1).map((item) => (
              <div
                key={item.label}
                className="border-b border-gray-100 last:border-0"
              >
                <button
                  className="w-full flex items-center justify-between px-1 py-3.5 text-gray-800 font-medium text-sm"
                  onClick={() =>
                    setActiveNav(activeNav === item.label ? null : item.label)
                  }
                >
                  {item.label}
                  {item.children && (
                    <ChevronDown
                      size={15}
                      className={`transition-transform ${activeNav === item.label ? "rotate-180" : ""}`}
                    />
                  )}
                </button>
                {item.children && activeNav === item.label && (
                  <div className="bg-gray-50 px-4 pb-3 rounded-lg mb-2">
                    {item.children.map((child) => (
                      <a
                        key={child}
                        href="#"
                        className="block py-2 text-gray-600 text-sm hover:text-[#c8102e]"
                      >
                        {child}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </header>
  );
}
