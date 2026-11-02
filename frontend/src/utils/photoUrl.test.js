import assert from 'node:assert/strict';
import test from 'node:test';
import { createPhotoUrlResolver } from './photoUrl.js';

const productionResolver = createPhotoUrlResolver('https://neighborlend-api.example/api');

test('keeps public Supabase Storage URLs unchanged', () => {
  const url = 'https://project.supabase.co/storage/v1/object/public/listing_photos/images/item.jpg';
  assert.equal(productionResolver(url), url);
});

test('rewrites localhost uploads to the configured backend origin', () => {
  assert.equal(
    productionResolver('http://localhost:8000/uploads/images/item.jpg'),
    'https://neighborlend-api.example/uploads/images/item.jpg',
  );
});

test('rewrites private LAN upload URLs while preserving query and fragment', () => {
  assert.equal(
    productionResolver('http://192.168.1.25:8000/uploads/images/item.jpg?v=2#cover'),
    'https://neighborlend-api.example/uploads/images/item.jpg?v=2#cover',
  );
});

test('keeps unrelated external URLs unchanged', () => {
  const url = 'https://cdn.example.com/listings/item.jpg';
  assert.equal(productionResolver(url), url);
});

test('relative upload paths use the API origin when configured', () => {
  assert.equal(
    productionResolver('/uploads/images/item.jpg'),
    'https://neighborlend-api.example/uploads/images/item.jpg',
  );
});
