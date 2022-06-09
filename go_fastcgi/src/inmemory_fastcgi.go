package main

import (
	"fmt"
	"io/ioutil"
	"log"
	"net"
	"net/http"
	"net/http/fcgi"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"bou.ke/monkey"

	"MahimahiProtobufs"

	"github.com/golang/protobuf/proto"
)

type Handler struct{}

func contains(arr []string, str string) bool {
	for _, a := range arr {
		if a == str {
			return true
		}
	}
	return false
}

func unchunk(body []byte) string {
	offset := 0
	length := len(body)
	out := ""
	tmp := ""
	overall_length := 0
	for {
		if offset+1 > length {
			break
		}
		e := string(body[offset : offset+1])
		offset += 1
		tmp += e
		if len(tmp) > 8 {
			return string(body)
		}
		if len(tmp) >= 2 && tmp[len(tmp)-2:] == "\r\n" {
			cl, err := strconv.ParseInt(tmp[:len(tmp)-2], 16, 64)
			if err != nil {
				log.Printf("%s\n", body)
				log.Panic(err)
			}
			chunklength := int(cl)
			tmp = ""
			overall_length += chunklength

			if overall_length > 10*1024*1024 {
				fmt.Println(overall_length)
				log.Panic("chunks use more than 10MB?!")
			}

			if offset+chunklength > length {
				log.Panic("unexpected end of chunk")
			}

			chunk := string(body[offset : offset+chunklength])
			offset += chunklength
			out += chunk

			if offset+2 > length {
				log.Panic("missing \\r\\n after chunk")
			}

			tail := string(body[offset : offset+2])
			offset += 2

			if tail != "\r\n" {
				log.Panic("chunk does not end with \\r\\n")
			}
		}
	}

	return out
}

type CacheKey struct {
	method string
	keyuri string
	host   string
	https  bool
}

type CacheEntries struct {
	entries []CacheEntry
}

type KV struct {
	k, v string
}

type CacheEntry struct {
	request_uri               string
	response_status           int
	response_headers_stripped []KV
	response_body             string
	request_headers           map[string]KV
}

var cache map[CacheKey]*CacheEntries

func preloadFiles(workdir string) {
	matches, err := filepath.Glob(workdir + "/*.save")
	if err != nil {
		fmt.Println(err)
	}
	for _, f := range matches {
		file, err := os.Open(f)
		if err != nil {
			fmt.Println(err)
		}
		data, err := ioutil.ReadAll(file)
		if err != nil {
			fmt.Println(err)
		}
		rr := &MahimahiProtobufs.RequestResponse{}
		err = proto.Unmarshal(data, rr)
		if err != nil {
			fmt.Println(err)
		}

		https := (*rr.Scheme == MahimahiProtobufs.RequestResponse_HTTPS)

		request_headers := make(map[string]KV)
		for _, request_header := range rr.Request.Header {
			k := string(request_header.Key)
			v := string(request_header.Value)
			k_stripped := strings.ToLower(strings.TrimSpace(k))
			request_headers[k_stripped] = KV{k, v}
		}

		response_headers := make(map[string]KV)
		response_headers_stripped := make([]KV, 0)
		for _, response_header := range rr.Response.Header {
			k := string(response_header.Key)
			v := string(response_header.Value)
			k_stripped := strings.ToLower(strings.TrimSpace(k))

			if len(k_stripped) == 0 {
				continue
			}

			response_headers[k_stripped] = KV{k, v}

			if !contains([]string{"expires", "date", "last-modified",
				"link", "alt-svc", "connection", "transfer-encoding"}, k_stripped) {
				response_headers_stripped = append(response_headers_stripped, KV{k, v})
			}
		}

		transfer_encoding_val, transfer_encoding_ok := response_headers["transfer-encoding"]
		chunked := transfer_encoding_ok && strings.Contains(transfer_encoding_val.v, "chunked")

		var response_body string
		if chunked {
			response_body = unchunk(rr.Response.Body)
		} else {
			response_body = string(rr.Response.Body)
		}

		response_line := string(rr.Response.FirstLine)
		request_line := string(rr.Request.FirstLine)

		reqls := strings.Split(request_line, " ")
		if len(reqls) != 3 {
			log.Panic("request line has more than 3 entries")
		}

		request_method := reqls[0]
		request_uri := reqls[1]

		request_keyuri := strings.Split(request_uri, "?")[0]
		request_host := request_headers["host"].v

		resls := strings.Split(response_line, " ")
		if len(resls) < 2 {
			log.Panic("response line has less than")
		}

		resstatus, err := strconv.ParseInt(resls[1], 10, 64)
		if err != nil {
			fmt.Println(err)
		}
		response_status := int(resstatus)

		request_key := CacheKey{request_method, request_keyuri, request_host, https}

		cache_entries, cached_ok := cache[request_key]

		if !cached_ok {
			cache_entries = &CacheEntries{make([]CacheEntry, 0)}
			cache[request_key] = cache_entries
		}

		cache_entry := CacheEntry{request_uri, response_status, response_headers_stripped, response_body, request_headers}
		cache_entries.entries = append(cache_entries.entries, cache_entry)
	}
}

func (s Handler) ServeHTTP(w http.ResponseWriter, req *http.Request) {
	request_uri := req.URL.RequestURI()
	request_method := req.Method
	request_host := req.Host

	ifnonematchhash := req.Header.Get("if-none-match")

	https := (req.URL.Scheme == "https")

	request_keyuri := strings.Split(request_uri, "?")[0]

	request_key := CacheKey{request_method, request_keyuri, request_host, https}

	cache_entries, cached_ok := cache[request_key]

	if cached_ok {
		var entry CacheEntry
		best_fit := -1

		for _, e := range cache_entries.entries {
			i_start := len(request_keyuri)
			i_end := len(request_uri)
			if i_end > len(e.request_uri) {
				i_end = len(e.request_uri)
			}
			fit := 0
			for i := i_start; i < i_end; i++ {
				if request_uri[i] != e.request_uri[i] {
					break
				}
				fit += 1
			}
			if fit >= best_fit {
				ifnonematchentry, ifnonematchentry_ok := e.request_headers["if-none-match"]
				if e.response_status == 304 && ifnonematchentry_ok && ifnonematchentry.v == ifnonematchhash {
					entry = e
					best_fit = fit
					break
				} else if e.response_status == 200 {
					entry = e
					best_fit = fit
				} else if fit > best_fit {
					entry = e
					best_fit = fit
				}
			}
		}
		headers := w.Header()
		for _, kv := range entry.response_headers_stripped {
			headers.Add(kv.k, kv.v)
		}
		w.WriteHeader(entry.response_status)
		w.Write([]byte(entry.response_body))
	} else {
		headers := w.Header()
		headers.Add("content-type", "text/plain")
		w.WriteHeader(404)
		w.Write([]byte("NOT FOUND"))
	}
}

func main() {
	fmt.Println("Starting server...")
	workdir := os.Args[1]
	socketfile := os.Args[2]
	pidfile := os.Args[3]

	ioutil.WriteFile(pidfile, []byte(fmt.Sprintf("%d", os.Getpid())), 0664)

	cache = make(map[CacheKey]*CacheEntries)
	preloadFiles(workdir)

	//fix parseHTTPVersion which cannot handle HTTP/3
	monkey.Patch(http.ParseHTTPVersion, func(vers string) (major, minor int, ok bool) {
		switch vers {
		case "HTTP/1.1":
			return 1, 1, true
		case "HTTP/1.0":
			return 1, 0, true
		case "HTTP/2.0":
			return 2, 0, true
		case "HTTP/2":
			return 2, 0, true
		case "HTTP/3":
			return 3, 0, true
		case "HTTP/3.0":
			return 3, 0, true
		}
		return 0, 0, false
	})

	l, err1 := net.Listen("unix", socketfile)
	if err1 != nil {
		log.Fatal(err1)
	}
	err2 := os.Chmod(socketfile, 0777)
	if err2 != nil {
		log.Fatal(err2)
	}
	defer l.Close()
	b := &Handler{}
	err := fcgi.Serve(l, b)
	if err != nil {
		log.Fatal(err)
	}
}
