
use base64;
use rocket::{
    request,
    Request,
    Outcome,
    outcome::IntoOutcome,
    http::Status,
    request::FromRequest
};

#[derive(Debug)]
pub struct BasicAuth {
    pub username: String,
    pub password: String,
}

impl<'a, 'r> FromRequest<'a, 'r> for BasicAuth {
    type Error = ();

    fn from_request(request: &Request) -> request::Outcome<Self, Self::Error> {
        let auth_header = request.headers().get_one("Authorization");
        if let Some(auth_header) = auth_header {
            let split = auth_header.split_whitespace().collect::<Vec<_>>();
            if split.len() != 2 {
                return Outcome::Failure((Status::Unauthorized, ()));
            }
            let (basic, payload) = (split[0], split[1]);
            if basic != "Basic" {
                return Outcome::Failure((Status::Unauthorized, ()));
            }
            let decoded = base64::decode(payload)
                .ok()
                .into_outcome((Status::BadRequest, ()))?;

            let decoded_str = String::from_utf8(decoded)
                .ok()
                .into_outcome((Status::BadRequest, ()))?;

            let split = decoded_str.split(":").collect::<Vec<_>>();

            // If exactly username & password pair are present
            if split.len() != 2 {
                return Outcome::Failure((Status::BadRequest, ()));
            }

            let (username, password) = (split[0].to_string(), split[1].to_string());

            Outcome::Success(BasicAuth {
                username,
                password
            })
        } else {
            Outcome::Failure((Status::Unauthorized, ()))
        }
    }
}