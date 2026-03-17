"use client";

import { useState, useCallback } from "react";
import { Search, Sparkles, ExternalLink, Star, ChevronLeft, ChevronRight } from "lucide-react";
import { searchOutfits, getOutfits, Outfit, Product, PaginatedResponse } from "@/lib/api";
import clsx from "clsx";

// ── Vibe suggestions ──
const VIBE_SUGGESTIONS = [
  { label: "Date Night", query: "date-night", emoji: "🌹" },
  { label: "Casual", query: "casual", emoji: "☀️" },
  { label: "Streetwear", query: "streetwear", emoji: "🔥" },
  { label: "Retro / 90s", query: "retro", emoji: "📼" },
  { label: "Minimalist", query: "minimalist", emoji: "◻️" },
  { label: "Summer", query: "summer", emoji: "🏖️" },
  { label: "Boho", query: "boho", emoji: "🌻" },
  { label: "Formal", query: "formal", emoji: "👔" },
  { label: "Sporty", query: "sporty", emoji: "🏃" },
  { label: "Winter", query: "winter", emoji: "❄️" },
];

// ── Source badge colors ──
const SOURCE_COLORS: Record<string, string> = {
  ZAPPOS: "bg-teal-100 text-teal-800",
  AMAZON: "bg-orange-100 text-orange-800",
  SSENSE: "bg-purple-100 text-purple-800",
};

const SOURCE_LABELS: Record<string, string> = {
  ZAPPOS: "Zappos",
  AMAZON: "Amazon",
  SSENSE: "SSENSE",
};

// ── Product Card ──
function ProductCard({ product, label }: { product: Product; label: string }) {
  return (
    <div className="group relative">
      <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
        {label}
      </div>
      <a
        href={product.product_url}
        target="_blank"
        rel="noopener noreferrer"
        className="block card overflow-hidden hover:ring-2 hover:ring-brand-400 transition-all"
      >
        {/* Image */}
        <div className="relative aspect-square overflow-hidden bg-gray-100">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name}
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
              loading="lazy"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-gray-300">
              <Sparkles size={32} />
            </div>
          )}

          {/* Source badge */}
          <span
            className={clsx(
              "absolute top-2 left-2 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase",
              SOURCE_COLORS[product.source] || "bg-gray-100 text-gray-700"
            )}
          >
            {SOURCE_LABELS[product.source] || product.source}
          </span>

          {/* External link icon */}
          <div className="absolute top-2 right-2 rounded-full bg-white/80 p-1.5 opacity-0 transition-opacity group-hover:opacity-100">
            <ExternalLink size={12} className="text-gray-600" />
          </div>
        </div>

        {/* Info */}
        <div className="p-3">
          <p className="text-sm font-medium text-gray-900 line-clamp-2 leading-tight">
            {product.name}
          </p>
          {product.brand && (
            <p className="mt-0.5 text-xs text-gray-500">{product.brand}</p>
          )}
          {product.google_product_category && (
            <p className="mt-1 text-[10px] text-gray-400 line-clamp-1" title={product.google_product_category}>
              {product.google_product_category.split(" > ").slice(-2).join(" › ")}
            </p>
          )}
          <div className="mt-2 flex items-center justify-between">
            <span className="text-sm font-bold text-brand-700">
              ${product.price.toFixed(2)}
            </span>
            {product.color && (
              <span className="text-xs text-gray-400">{product.color}</span>
            )}
          </div>
        </div>
      </a>
    </div>
  );
}

// ── Outfit Card ──
function OutfitCard({ outfit }: { outfit: Outfit }) {
  const totalPrice =
    outfit.top.price +
    outfit.bottom.price +
    outfit.shoe.price +
    outfit.accessory.price;

  return (
    <div className="card p-5">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Star size={16} className="text-yellow-500 fill-yellow-500" />
          <span className="text-sm font-semibold text-gray-700">
            Score: {(outfit.score * 100).toFixed(0)}%
          </span>
        </div>
        <span className="text-sm font-bold text-gray-900">
          Total: ${totalPrice.toFixed(2)}
        </span>
      </div>

      {/* Style tags */}
      <div className="mb-4 flex flex-wrap gap-1.5">
        {outfit.style_tags.map((tag) => (
          <span
            key={tag}
            className="badge-primary text-[11px]"
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Product grid */}
      <div className="grid grid-cols-2 gap-3">
        <ProductCard product={outfit.top} label="Top" />
        <ProductCard product={outfit.bottom} label="Bottom" />
        <ProductCard product={outfit.shoe} label="Shoes" />
        <ProductCard product={outfit.accessory} label="Accessory" />
      </div>
    </div>
  );
}

// ── Skeleton Loader ──
function OutfitSkeleton() {
  return (
    <div className="card p-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="skeleton h-4 w-24 rounded" />
        <div className="skeleton h-4 w-20 rounded" />
      </div>
      <div className="mb-4 flex gap-1.5">
        <div className="skeleton h-5 w-16 rounded-full" />
        <div className="skeleton h-5 w-20 rounded-full" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i}>
            <div className="skeleton mb-2 h-3 w-12 rounded" />
            <div className="skeleton aspect-square rounded-xl" />
            <div className="mt-2 space-y-1.5">
              <div className="skeleton h-3 w-full rounded" />
              <div className="skeleton h-3 w-16 rounded" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Page ──
export default function HomePage() {
  const [query, setQuery] = useState("");
  const [activeVibe, setActiveVibe] = useState("");
  const [outfits, setOutfits] = useState<Outfit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    pages: 0,
  });
  const [hasSearched, setHasSearched] = useState(false);

  const performSearch = useCallback(
    async (searchQuery: string, page: number = 1) => {
      if (!searchQuery.trim()) return;
      setLoading(true);
      setError(null);
      setHasSearched(true);

      try {
        const result = await searchOutfits(searchQuery, page);
        setOutfits(result.items);
        setPagination({
          total: result.total,
          page: result.page,
          pages: result.pages,
        });
      } catch (err: any) {
        console.error("Search failed:", err);
        if (err?.response?.status === 422) {
          setError("Please enter a valid search term.");
        } else {
          setError("Failed to fetch outfits. Make sure the API server is running.");
        }
        setOutfits([]);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const loadAllOutfits = useCallback(async (page: number = 1) => {
    setLoading(true);
    setError(null);
    setHasSearched(true);
    setActiveVibe("");
    setQuery("");

    try {
      const result = await getOutfits(page);
      setOutfits(result.items);
      setPagination({
        total: result.total,
        page: result.page,
        pages: result.pages,
      });
    } catch (err) {
      console.error("Failed to load outfits:", err);
      setError("Failed to fetch outfits. Make sure the API server is running.");
      setOutfits([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      setActiveVibe(query.trim().toLowerCase().replace(/\s+/g, "-"));
      performSearch(query.trim());
    }
  };

  const handleVibeClick = (vibe: { label: string; query: string }) => {
    setQuery(vibe.label);
    setActiveVibe(vibe.query);
    performSearch(vibe.query);
  };

  return (
    <main className="min-h-screen">
      {/* Hero Section */}
      <header className="relative overflow-hidden bg-gradient-to-br from-brand-50 via-white to-brand-50">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmOWE4YTgiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMiIvPjwvZz48L2c+PC9zdmc+')] opacity-50" />
        <div className="relative mx-auto max-w-5xl px-4 pb-12 pt-16 sm:px-6 lg:px-8">
          {/* Title */}
          <div className="text-center">
            <h1 className="font-display text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl lg:text-6xl">
              Mini Outfit
              <span className="text-brand-600"> Builder</span>
            </h1>
            <p className="mx-auto mt-4 max-w-2xl text-lg text-gray-600">
              AI-curated outfits from Zappos, Amazon &amp; SSENSE.
              Search by vibe and discover your next look.
            </p>
          </div>

          {/* Search Bar */}
          <form onSubmit={handleSearch} className="mx-auto mt-8 max-w-xl">
            <div className="relative flex items-center">
              <Search
                size={20}
                className="absolute left-4 text-gray-400"
              />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search a vibe... (e.g., date night, casual, retro)"
                className="input pl-12 pr-28 py-3.5 text-base rounded-xl"
              />
              <button type="submit" className="btn-primary absolute right-1.5 rounded-lg px-5 py-2">
                Search
              </button>
            </div>
          </form>

          {/* Vibe Chips */}
          <div className="mx-auto mt-6 flex max-w-3xl flex-wrap items-center justify-center gap-2">
            <button
              onClick={() => loadAllOutfits()}
              className={clsx(
                "rounded-full px-4 py-1.5 text-sm font-medium transition-all",
                !activeVibe && hasSearched
                  ? "bg-brand-600 text-white shadow-md"
                  : "bg-white text-gray-600 shadow-sm hover:bg-gray-50 border border-gray-200"
              )}
            >
              ✨ All Outfits
            </button>
            {VIBE_SUGGESTIONS.map((vibe) => (
              <button
                key={vibe.query}
                onClick={() => handleVibeClick(vibe)}
                className={clsx(
                  "rounded-full px-4 py-1.5 text-sm font-medium transition-all",
                  activeVibe === vibe.query
                    ? "bg-brand-600 text-white shadow-md"
                    : "bg-white text-gray-600 shadow-sm hover:bg-gray-50 border border-gray-200"
                )}
              >
                {vibe.emoji} {vibe.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Results Section */}
      <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        {/* Status bar */}
        {hasSearched && !loading && !error && (
          <div className="mb-6 flex items-center justify-between">
            <p className="text-sm text-gray-500">
              {pagination.total > 0 ? (
                <>
                  Showing{" "}
                  <span className="font-semibold text-gray-900">
                    {outfits.length}
                  </span>{" "}
                  of{" "}
                  <span className="font-semibold text-gray-900">
                    {pagination.total}
                  </span>{" "}
                  outfits
                  {activeVibe && (
                    <> for <span className="font-semibold text-brand-600">"{activeVibe}"</span></>
                  )}
                </>
              ) : (
                "No outfits found. Try a different vibe!"
              )}
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mx-auto max-w-md rounded-xl border border-red-200 bg-red-50 p-6 text-center">
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={() => loadAllOutfits()}
              className="btn-secondary mt-4 text-sm"
            >
              Try loading all outfits
            </button>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="grid gap-6 sm:grid-cols-1 lg:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <OutfitSkeleton key={i} />
            ))}
          </div>
        )}

        {/* Outfits Grid */}
        {!loading && outfits.length > 0 && (
          <div className="grid gap-6 sm:grid-cols-1 lg:grid-cols-2 xl:grid-cols-3">
            {outfits.map((outfit) => (
              <OutfitCard key={outfit.id} outfit={outfit} />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && !hasSearched && (
          <div className="py-20 text-center">
            <Sparkles size={48} className="mx-auto mb-4 text-brand-300" />
            <h2 className="text-xl font-semibold text-gray-700">
              Discover Your Perfect Outfit
            </h2>
            <p className="mx-auto mt-2 max-w-md text-gray-500">
              Search by vibe or click a style above to see AI-curated outfit combinations
              from top fashion retailers.
            </p>
          </div>
        )}

        {/* Pagination */}
        {!loading && pagination.pages > 1 && (
          <div className="mt-10 flex items-center justify-center gap-3">
            <button
              onClick={() => {
                const newPage = Math.max(1, pagination.page - 1);
                if (activeVibe) performSearch(activeVibe, newPage);
                else loadAllOutfits(newPage);
              }}
              disabled={pagination.page <= 1}
              className="btn-secondary disabled:opacity-40"
            >
              <ChevronLeft size={16} className="mr-1" /> Previous
            </button>
            <span className="text-sm text-gray-600">
              Page {pagination.page} of {pagination.pages}
            </span>
            <button
              onClick={() => {
                const newPage = Math.min(pagination.pages, pagination.page + 1);
                if (activeVibe) performSearch(activeVibe, newPage);
                else loadAllOutfits(newPage);
              }}
              disabled={pagination.page >= pagination.pages}
              className="btn-secondary disabled:opacity-40"
            >
              Next <ChevronRight size={16} className="ml-1" />
            </button>
          </div>
        )}
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white py-8">
        <div className="mx-auto max-w-5xl px-4 text-center">
          <p className="text-sm text-gray-400">
            Mini Outfit Builder &middot; Products from Zappos, Amazon &amp; SSENSE
          </p>
          <p className="mt-1 text-xs text-gray-300">
            Prices and availability are updated daily. Click any product to visit the retailer.
          </p>
        </div>
      </footer>
    </main>
  );
}
