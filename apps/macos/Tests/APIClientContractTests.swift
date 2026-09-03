import Foundation
import XCTest
@testable import NeuralMemoryAgent

final class APIClientContractTests: XCTestCase {
    func testHealthRequiresExactServiceIdentityAndSuccessStatus() {
        let valid = Data(#"{"status":"ok","service":"neural-memory","version":"0.2.0"}"#.utf8)
        let unrelated = Data(#"{"status":"ok","service":"another-app","version":"1"}"#.utf8)

        XCTAssertTrue(APIClient.isNeuralMemoryHealthResponse(data: valid, statusCode: 200))
        XCTAssertFalse(APIClient.isNeuralMemoryHealthResponse(data: valid, statusCode: 404))
        XCTAssertFalse(APIClient.isNeuralMemoryHealthResponse(data: unrelated, statusCode: 200))
        XCTAssertFalse(APIClient.isNeuralMemoryHealthResponse(data: Data("not json".utf8), statusCode: 200))
    }

    func testAuthorizationRejectsAnEmptyToken() throws {
        XCTAssertThrowsError(try APIClient.authorizationHeader(token: "   "))
        XCTAssertEqual(try APIClient.authorizationHeader(token: " abc "), "Bearer abc")
    }
}
