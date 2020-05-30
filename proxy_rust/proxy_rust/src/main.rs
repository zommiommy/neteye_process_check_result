#![feature(proc_macro_hygiene, decl_macro)]

#[macro_use] extern crate rocket;
use rocket::response::{content, status};
use rocket::http::RawStr;
use rocket::http::Status;
use uuid::Uuid;
use std::sync::{Arc, Mutex};
use std::collections::{
    BinaryHeap,
    HashMap
};
use std::{
    thread,
    time
};
use reqwest;
use core::arch::x86::_rdtsc;
mod basic_auth;

fn rdtsc() -> u64 {
    // only for x86
    unsafe{
        _rdtsc()
    }
}

enum RequestMethod{
    GET, POST, PUT
}

struct Task{
    id : u64,
    priority: u64,
    method: RequestMethod,
    url : String,
    body : String,
    username : String,
    password : String,
}

struct Result{
    id : u64,
    error_code: u16,
    body: String,
}

static mut queue   : Arc<Mutex<BinaryHeap<Task>>>;
static mut results : Arc<Mutex<HashMap<u64, Result>>>;

#[get("/")]
fn index() -> &'static str {
    "Hello, world!"
}

#[put("/v1/objects/services/<host_service>", data = "<input>")]
fn test(host_service: &RawStr, input : String, auth: basic_auth::BasicAuth) -> String {
    // get the host and service
    let tokens:Vec<&str>= host_service.as_str().split("!").collect();
    let host = tokens[0];
    let service = tokens[1];
    // forward the request
    println!("Forwarding the request to {}!{}", host, service);
    let id = rdtsc();//Uuid::new_v4();
    queue.lock().insert(
        Task{
            id: id,
            priority: rdtsc(),
            method: RequestMethod::PUT,
            url: "http://localhost:8888/v1/objects/services/host!service",
            body: input,
            username: auth.username,
            password: auth.password
        }
    )
    while !results.contains_key(id){
        thread::sleep_ms(time::Duration::from_millis(10));
    }
    results.remove(id)
}

#[catch(404)]
fn not_found(req: &rocket::Request) -> content::Html<String> {
    content::Html(format!("<p>Sorry, but '{}' is not a valid path!</p>
            <p>Try visiting /hello/&lt;name&gt;/&lt;age&gt; instead.</p>",
            req.uri()))
}


fn requests_executor(){
    let client = reqwest::blocking::Client::new();
    let queue = Arc::clone(&queue);
    let results = Arc::clone(&results);
    loop {
        // use the lock to get the task from the queue
        let mut task : Task;
        {
            let queue = *queue.get_mut().unwrap();
            task = queue.pop();
        }
        // Translate the method to a function
        let result = match task.method {
            RequestMethod::GET  => { client.get(&task.url)  },
            RequestMethod::PUT  => { client.put(&task.url)  },
            RequestMethod::POST => { client.post(&task.url) },
            }
            .body(task.body)
            .basic_auth(
                task.username,
                Some(task.password)
            )
            .send()
            .unwrap();
            
        // add the result ot the results
        {
            results.get_mut().unwrap().insert(
                task.id,
                Result{
                    id:task.id,
                    error_code: result.status().as_u16(),
                    body: result.text().unwrap()
                }
            ).unwrap();
        }
    }
}

fn main() {
    // launch the request executor
    thread::spawn(|| {
        requests_executor();
    });
    // launch the server
    rocket::ignite()
        .register(catchers![
            not_found
        ])
        .mount("/", routes![
            index, 
            test
        ])
        .launch();
}