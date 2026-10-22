@IsTest
private class SmartSupportApiServiceTest {

    private class MockApiResponse implements HttpCalloutMock {
        public HTTPResponse respond(HTTPRequest request) {
            HttpResponse response = new HttpResponse();
            response.setStatusCode(200);
            response.setHeader('Content-Type', 'application/json');
            response.setBody('{"issues":[],"total":0}');
            return response;
        }
    }

    @IsTest
    static void testGetIssues() {
        Test.setMock(HttpCalloutMock.class, new MockApiResponse());

        Test.startTest();
        String result = SmartSupportApiService.getIssues(1);
        Test.stopTest();

        System.assertNotEquals(null, result);
        System.assert(result.contains('issues'));
    }
}
