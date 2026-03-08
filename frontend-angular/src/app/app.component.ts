import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { ProductService } from './services/product.service';
import { Product, SearchResult, ComparedProduct } from './models/product.model';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule],
  providers: [ProductService],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  query = '';
  loading = false;
  error = '';
  result: SearchResult | null = null;
  comparedProducts: ComparedProduct[] = [];
  recentSearches: string[] = [];
  searchSubject = new Subject<string>();
  viewMode: 'compare' | 'dia' | 'coto' = 'compare';
  sortBy: 'price' | 'name' | 'discount' = 'price';
  backendOnline = false;

  constructor(private productService: ProductService) {}

  ngOnInit() {
    this.recentSearches = JSON.parse(localStorage.getItem('supercompare_searches') || '[]');
    this.checkBackend();
    this.searchSubject.pipe(
      debounceTime(500),
      distinctUntilChanged()
    ).subscribe(q => {
      if (q.trim().length >= 2) this.doSearch(q);
    });
  }

  checkBackend() {
    this.productService.checkHealth().subscribe({
      next: () => this.backendOnline = true,
      error: () => this.backendOnline = false
    });
  }

  onSearchInput() { this.searchSubject.next(this.query); }

  search() {
    if (this.query.trim().length < 2) return;
    this.doSearch(this.query.trim());
  }

  doSearch(q: string) {
    this.loading = true;
    this.error = '';
    this.result = null;
    this.comparedProducts = [];

    if (!this.recentSearches.includes(q)) {
      this.recentSearches = [q, ...this.recentSearches].slice(0, 6);
      localStorage.setItem('supercompare_searches', JSON.stringify(this.recentSearches));
    }

    this.productService.searchProducts(q).subscribe({
      next: (res) => {
        this.result = res;
        this.comparedProducts = this.buildFromBackendComparisons(res);
        this.loading = false;
      },
      error: () => {
        this.error = 'No se pudo conectar con el servidor. ¿Está corriendo el backend?';
        this.loading = false;
      }
    });
  }

  buildFromBackendComparisons(result: SearchResult): ComparedProduct[] {
    const comparisons = result?.comparisons || [];

    const compared: ComparedProduct[] = comparisons.map((c: any) => {
      const dia: Product | undefined  = c.dia  ? this.mapProduct(c.dia,  'dia')  : undefined;
      const coto: Product | undefined = c.coto ? this.mapProduct(c.coto, 'coto') : undefined;

      let cheapest: 'dia' | 'coto' | 'equal' | 'unknown' = 'unknown';
      let priceDiff: number | undefined;
      let priceDiffPercent: number | undefined;

      if (dia && coto) {
        if (dia.price < coto.price) {
          cheapest = 'dia';
          priceDiff = Math.round(coto.price - dia.price);
          priceDiffPercent = Math.round((priceDiff / coto.price) * 100);
        } else if (coto.price < dia.price) {
          cheapest = 'coto';
          priceDiff = Math.round(dia.price - coto.price);
          priceDiffPercent = Math.round((priceDiff / dia.price) * 100);
        } else {
          cheapest = 'equal';
          priceDiff = 0;
        }
      } else if (dia) {
        cheapest = 'dia';
      } else if (coto) {
        cheapest = 'coto';
      }

      return { dia, coto, cheapest, priceDiff, priceDiffPercent };
    });

    return this.sortProducts(compared);
  }

  private mapProduct(p: any, store: 'dia' | 'coto'): Product {
    // Use ProductService.mapProduct to ensure consistent field mapping
    return this.productService.mapProduct(p, store);
  }

  sortProducts(products: ComparedProduct[]): ComparedProduct[] {
    return [...products].sort((a, b) => {
      if (this.sortBy === 'price') {
        const aPrice = Math.min(a.dia?.price ?? Infinity, a.coto?.price ?? Infinity);
        const bPrice = Math.min(b.dia?.price ?? Infinity, b.coto?.price ?? Infinity);
        return aPrice - bPrice;
      }
      if (this.sortBy === 'discount') {
        const aDisc = Math.max(a.dia?.discount_percent ?? 0, a.coto?.discount_percent ?? 0);
        const bDisc = Math.max(b.dia?.discount_percent ?? 0, b.coto?.discount_percent ?? 0);
        return bDisc - aDisc;
      }
      const aName = (a.dia?.name || a.coto?.name || '').toLowerCase();
      const bName = (b.dia?.name || b.coto?.name || '').toLowerCase();
      return aName.localeCompare(bName);
    });
  }

  onSortChange() {
    if (this.result) this.comparedProducts = this.sortProducts(this.comparedProducts);
  }

  useRecent(s: string) { this.query = s; this.doSearch(s); }

  clearSearch() { this.query = ''; this.result = null; this.error = ''; }

  formatPrice(price: number): string {
    return price.toLocaleString('es-AR', { style: 'currency', currency: 'ARS', minimumFractionDigits: 2 });
  }

  get totalDia(): number  { return this.result?.total_dia  || 0; }
  get totalCoto(): number { return this.result?.total_coto || 0; }

  get cheaperDiaCount(): number {
    return this.comparedProducts.filter(p => p.cheapest === 'dia' && p.dia && p.coto).length;
  }
  get cheaperCotoCount(): number {
    return this.comparedProducts.filter(p => p.cheapest === 'coto' && p.dia && p.coto).length;
  }
}
