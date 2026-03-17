"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Star, ExternalLink, Sparkles } from "lucide-react";
import { getOutfitById, Outfit, Product } from "@/lib/api";
import clsx from "clsx";

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

function DetailProductCard({ product, label }: { product: Product; label: string }) {
  return (
    <a
      href={product.product_url}
      target="_blank"
      rel="noopener noreferrer"
      className="card group flex gap-4 p-4 hover:ring-2 hover:ring-brand-400 transition-all"
    >
      <div className="relative h-32 w-32 flex-shrink-0 overflow-hidden rounded-lg bg-gray-100">
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.name}
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-gray-300">
            <Sparkles size={24} />
          </div>
        )}
      </div>
      <div className="flex flex-1 flex-col justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-gray-400">{label}</p>
          <h3 className="mt-1 text-lg font-semibold text-gray-900">{product.name}</h3>
          {product.brand && (
            <p className="text-sm text-gray-500">{product.brand}</p>
          )}
          {product.google_product_category && (
            <p className="mt-0.5 text-[11px] text-gray-400" title={product.google_product_category}>
              📂 {product.google_product_category.split(" > ").slice(-2).join(" › ")}
            </p>
          )}
          {product.description && (
            <p className="mt-1 text-sm text-gray-600 line-clamp-2">{product.description}</p>
          )}
        </div>
        <div className="mt-2 flex items-center justify-between">
          <span className="text-lg font-bold text-brand-700">
            ${product.price.toFixed(2)}
          </span>
          <div className="flex items-center gap-2">
            <span
              className={clsx(
                "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase",
                SOURCE_COLORS[product.source]
              )}
            >
              {SOURCE_LABELS[product.source]}
            </span>
            <ExternalLink size={14} className="text-gray-400 group-hover:text-brand-600" />
          </div>
        </div>
      </div>
    </a>
  );
}

export default function OutfitDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [outfit, setOutfit] = useState<Outfit | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (params.id) {
      getOutfitById(params.id as string)
        .then(setOutfit)
        .catch((err) => {
          console.error(err);
          setError("Outfit not found.");
        })
        .finally(() => setLoading(false));
    }
  }, [params.id]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-200 border-t-brand-600" />
      </div>
    );
  }

  if (error || !outfit) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <p className="text-red-600">{error || "Outfit not found"}</p>
        <button onClick={() => router.push("/")} className="btn-primary">
          Back to Home
        </button>
      </div>
    );
  }

  const totalPrice =
    outfit.top.price + outfit.bottom.price + outfit.shoe.price + outfit.accessory.price;

  return (
    <main className="min-h-screen bg-gray-50 py-8">
      <div className="mx-auto max-w-3xl px-4">
        {/* Back */}
        <button
          onClick={() => router.push("/")}
          className="mb-6 flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft size={16} /> Back to outfits
        </button>

        {/* Header */}
        <div className="mb-8">
          <h1 className="font-display text-3xl font-bold text-gray-900">
            Outfit Details
          </h1>
          <div className="mt-3 flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <Star size={16} className="text-yellow-500 fill-yellow-500" />
              <span className="text-sm font-semibold">
                {(outfit.score * 100).toFixed(0)}% match
              </span>
            </div>
            <span className="text-sm font-bold text-gray-900">
              Total: ${totalPrice.toFixed(2)}
            </span>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {outfit.style_tags.map((tag) => (
              <span key={tag} className="badge-primary">
                {tag}
              </span>
            ))}
          </div>
        </div>

        {/* Products */}
        <div className="space-y-4">
          <DetailProductCard product={outfit.top} label="Top" />
          <DetailProductCard product={outfit.bottom} label="Bottom" />
          <DetailProductCard product={outfit.shoe} label="Shoes" />
          <DetailProductCard product={outfit.accessory} label="Accessory" />
        </div>
      </div>
    </main>
  );
}
