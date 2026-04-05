"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "./AuthProvider";

export function Header() {
  const { isAuthenticated, userEmail, signOut } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  if (!isAuthenticated) return null;

  const links = [
    { href: "/", label: "Dashboard" },
    { href: "/trips", label: "Trips" },
    { href: "/cities", label: "Cities" },
    { href: "/bookings", label: "Bookings" },
  ];

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/" className="font-semibold text-lg text-gray-900">
          Travel
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-6">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              {l.label}
            </Link>
          ))}
          <span className="text-xs text-gray-400">{userEmail}</span>
          <button
            onClick={signOut}
            className="text-sm text-red-600 hover:text-red-800"
          >
            Log out
          </button>
        </nav>

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle menu"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {menuOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <nav className="md:hidden border-t border-gray-200 bg-white px-4 pb-4 pt-2 space-y-2">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="block py-2 text-gray-700"
              onClick={() => setMenuOpen(false)}
            >
              {l.label}
            </Link>
          ))}
          <div className="pt-2 border-t border-gray-100 text-xs text-gray-400">
            {userEmail}
          </div>
          <button
            onClick={signOut}
            className="block py-2 text-red-600"
          >
            Log out
          </button>
        </nav>
      )}
    </header>
  );
}
