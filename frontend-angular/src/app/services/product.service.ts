import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { Product, SearchResult } from '../models/product.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ProductService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  searchProducts(query: string): Observable<SearchResult> {
    const params = new HttpParams().set('q', query);
    return this.http.get<any>(`${this.apiUrl}/search`, { params }).pipe(
      map(res => ({
        query: res.query,
        total_dia: res.total_dia || 0,
        total_coto: res.total_coto || 0,
        comparisons: res.comparisons || [],
        dia: (res.dia_products || []).map((p: any) => this.mapProduct(p, 'dia')),
        coto: (res.coto_products || []).map((p: any) => this.mapProduct(p, 'coto')),
      }))
    );
  }

  mapProduct(p: any, store: 'dia' | 'coto'): Product {
    const image = p.image ?? p.image_url ?? null;
    const url = p.url ?? p.product_url ?? null;
    const on_sale = p.on_sale ?? p.is_on_sale ?? false;
    const discount = p.discount ?? p.discount_percent ?? null;
    return {
      name: p.name || '',
      price: p.price || 0,
      original_price: p.original_price ?? null,
      image,
      url,
      store,
      on_sale,
      discount_percent: discount,
      // Aliases for HTML template
      image_url: image,
      product_url: url,
      is_on_sale: on_sale,
      supermarket: store,
    };
  }

  checkHealth(): Observable<any> {
    return this.http.get(`${this.apiUrl}/health`);
  }
}
