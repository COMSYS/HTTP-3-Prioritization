from mahimahi import http_record_pb2
from glob import glob
import os
from io import BytesIO

cache = {}
def preload_files(workdir):
    files = glob(os.path.join(workdir, '*.save'))
    idx_entry = 0
    items = []
    for file in files:
        with open(file, 'rb') as f:
            rr = http_record_pb2.RequestResponse()
            rr.ParseFromString(f.read())

            https = rr.scheme == http_record_pb2.RequestResponse.Scheme.Value("HTTPS")
            
            request_headers = {}
            for request_header in rr.request.header:
                k = request_header.key.decode()
                v = request_header.value.decode()
                k_stripped = k.lower().strip()
                request_headers[k_stripped] = (k, v)

            response_headers = {}
            for response_header in rr.response.header:
                k = response_header.key.decode()
                v = response_header.value.decode()
                k_stripped = k.lower().strip()
                response_headers[k_stripped] = (k, v)

            response_headers_stripped = []
            for k, v in response_headers.items():
                if k not in ['expires', 'date', 'last-modified', 'link', 'alt-svc', 'connection', 'transfer-encoding']:
                    response_headers_stripped.append(v)

            response_line = rr.response.first_line.decode()
            request_line = rr.request.first_line.decode()

            request_method, request_uri, _ = request_line.split(' ')
            request_keyuri = request_uri.split('?',1)[0]
            request_host = request_headers['host'][1]

            _, response_status = response_line.split(' ', 1)

            request_key = (request_method, request_keyuri, request_host, https)

            if not request_key in cache:
                cache[request_key] = []
            item = {
                'request_uri': request_uri,
                'request_host': request_host,
                'request_method': request_method,
                'response_status': response_status,
                'response_headers': response_headers_stripped,
                'index': idx_entry
            }
            items.append(item)
            cache[request_key].append(item)
            idx_entry += 1

    return items

def calc_fit(a,b):
    fit = 0
    for i in range(0, min(len(a), len(b))):
        if a[i] != b[i]:
            break
        fit += 1
    return fit

def find_best_fit(method, uri, host, https):
    keyuri = uri.split('?',1)[0]
    key = (method, keyuri, host, https)

    if key in cache:
        best_fit = -1
        for item in cache[key]:
            item_uri = item['request_uri']
            fit = calc_fit(item_uri, uri)
            if fit > best_fit:
                best_fit_item = item
                best_fit = fit
    else:
        return None
    return best_fit_item
