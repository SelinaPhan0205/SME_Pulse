#!/usr/bin/env python3
"""Test Bills API"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Login với JSON body (không phải form data)
r = requests.post(f'{BASE_URL}/auth/login', json={'email': 'admin@sme.com', 'password': '123456'})
print('Login:', r.status_code)
if r.status_code != 200:
    print(r.text)
    exit(1)

token = r.json().get('access_token')
print('Token:', token[:50] + '...')
headers = {'Authorization': f'Bearer {token}'}

# Test bills API
print('\n--- Testing Bills API ---')
r2 = requests.get(f'{BASE_URL}/api/v1/bills?limit=5', headers=headers)
print('Bills API:', r2.status_code)
if r2.status_code == 200:
    data = r2.json()
    print('Total bills:', data.get('total'))
    print('Items count:', len(data.get('items', [])))
    for item in data.get('items', [])[:3]:
        supplier = item.get('supplier') or {}
        print(f"  Bill: {item['bill_no']}, supplier: {supplier.get('name')}, amount: {item['total_amount']}")
else:
    print(r2.text)

# Test invoices API
print('\n--- Testing Invoices API ---')
r3 = requests.get(f'{BASE_URL}/api/v1/invoices?limit=5', headers=headers)
print('Invoices API:', r3.status_code)
if r3.status_code == 200:
    data = r3.json()
    print('Total invoices:', data.get('total'))
    print('Items count:', len(data.get('items', [])))
    for item in data.get('items', [])[:3]:
        customer = item.get('customer') or {}
        print(f"  Invoice: {item['invoice_no']}, customer: {customer.get('name')}, amount: {item['total_amount']}, remaining: {item.get('remaining_amount')}")
else:
    print(r3.text)
