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
        dia: (res.dia_products || res.dia || []).map((p: any) => this.mapProduct(p, 'dia')),
        coto: (res.coto_products || res.coto || []).map((p: any) => this.mapProduct(p, 'coto')),
      }))
    );
  }

  private mapProduct(p: any, store: 'dia' | 'coto'): Product {
    return {
      name: p.name || '',
      price: p.price || 0,
      original_price: p.original_price || undefined,
      image_url: p.image || p.image_url || undefined,
      is_on_sale: p.on_sale || p.is_on_sale || false,
      discount_percent: p.discount || p.discount_percent || undefined,
      product_url: p.url || p.product_url || undefined,
      supermarket: store,
    };
  }

  checkHealth(): Observable<any> {
    return this.http.get(`${this.apiUrl}/health`);
  }
}
